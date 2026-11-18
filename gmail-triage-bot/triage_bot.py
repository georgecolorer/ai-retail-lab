import os
import json
import logging
import base64
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import truststore

truststore.inject_into_ssl()
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from gmail_connect import pripoj_gmail
from classifier import analyzuj_email, nacti_konfiguraci

HISTORY_FILE = "history.json"

# 12 oficiálních barev podporovaných Gmail API (uspořádáno pro 6x2 paletu)
GMAIL_BARVY = {
    "Šedá": {"backgroundColor": "#cccccc", "textColor": "#000000"},
    "Světle modrá": {"backgroundColor": "#a4c2f4", "textColor": "#000000"},
    "Tyrkysová": {"backgroundColor": "#89d3b2", "textColor": "#000000"},
    "Fialová": {"backgroundColor": "#a479e2", "textColor": "#ffffff"},
    "Růžová": {"backgroundColor": "#f691b3", "textColor": "#000000"},
    "Červená": {"backgroundColor": "#fb4c2f", "textColor": "#ffffff"},
    "Tmavě šedá": {"backgroundColor": "#666666", "textColor": "#ffffff"},
    "Modrá": {"backgroundColor": "#4a86e8", "textColor": "#ffffff"},
    "Petrolejová": {"backgroundColor": "#16a766", "textColor": "#ffffff"},
    "Oranžová": {"backgroundColor": "#ffad47", "textColor": "#000000"},
    "Žlutá": {"backgroundColor": "#fad165", "textColor": "#000000"},
    "Zelená": {"backgroundColor": "#43d692", "textColor": "#000000"},
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def uloz_do_historie(nove_zaznamy: list):
    if not nove_zaznamy:
        return
    historie = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8-sig") as f:
                historie = json.load(f)
        except Exception:
            historie = []
    
    existujici_ids = {z["id"] for z in historie}
    filtrovane_nove = [z for z in nove_zaznamy if z["id"] not in existujici_ids]
    aktualizovana = (filtrovane_nove + historie)[:500]
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(aktualizovana, f, ensure_ascii=False, indent=2)

def ziskej_nebo_vytvor_stitek(service, nazev_stitku: str, existujici_stitky: dict, barva_nazev: str = None) -> str:
    barva_obj = GMAIL_BARVY.get(barva_nazev) if barva_nazev else None

    if nazev_stitku in existujici_stitky:
        return existujici_stitky[nazev_stitku]
    
    body = {
        "name": nazev_stitku,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }
    if barva_obj:
        body["color"] = barva_obj

    novy_stitek = service.users().labels().create(userId="me", body=body).execute()
    existujici_stitky[nazev_stitku] = novy_stitek["id"]
    logging.info(f"Nový štítek v Gmailu vytvořen: {nazev_stitku} (barva: {barva_nazev or 'výchozí'})")
    return novy_stitek["id"]

def synchronizuj_barvy_stitku():
    service = pripoj_gmail()
    konfig = nacti_konfiguraci()
    odpoved_stitky = service.users().labels().list(userId="me").execute()
    existujici_stitky = {s["name"]: s["id"] for s in odpoved_stitky.get("labels", [])}

    id_urgent = ziskej_nebo_vytvor_stitek(service, "AI/P1-URGENT", existujici_stitky, "Červená")
    service.users().labels().patch(
        userId="me", id=id_urgent, body={"color": GMAIL_BARVY["Červená"]}
    ).execute()

    for nazev, info in konfig.get("kategorie", {}).items():
        plny_nazev = f"AI/{nazev}"
        barva_nazev = info.get("barva", "Šedá")
        barva_obj = GMAIL_BARVY.get(barva_nazev, GMAIL_BARVY["Šedá"])

        stitek_id = ziskej_nebo_vytvor_stitek(service, plny_nazev, existujici_stitky, barva_nazev)
        service.users().labels().patch(
            userId="me", id=stitek_id, body={"color": barva_obj}
        ).execute()

    logging.info("Barvy a štítky byly úspěšně synchronizovány do Gmailu.")

def vytahni_text_a_prilohy(payload: dict) -> tuple[str, list]:
    text = ""
    prilohy = []

    def projdi_casti(cast):
        nonlocal text
        filename = cast.get("filename", "")
        if filename:
            prilohy.append(filename)
        
        if "parts" in cast:
            for part in cast["parts"]:
                projdi_casti(part)
        elif cast.get("mimeType") == "text/plain" and "data" in cast.get("body", {}):
            if not text:
                text = base64.urlsafe_b64decode(cast["body"]["data"]).decode("utf-8", errors="ignore")

    projdi_casti(payload)
    return text, prilohy

def zpracuj_jednu_zpravu(msg_id: str):
    service = pripoj_gmail()
    detail = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    
    hlavicky = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
    odesilatel = hlavicky.get("From", "Neznámý odesílatel")
    predmet = hlavicky.get("Subject", "(Bez předmětu)")
    
    text_tela, prilohy = vytahni_text_a_prilohy(detail["payload"])
    text_tela = text_tela.strip() or detail.get("snippet", "")
    text_tela = text_tela[:2000]

    analyza = analyzuj_email(odesilatel, predmet, text_tela, ma_prilohu=bool(prilohy))
    return msg_id, odesilatel, predmet, prilohy, analyza

def spust_trideni(pocet_zprav: int = 15, jen_neprectene: bool = False, progress_callback=None):
    logging.info(f"=== Spouštím Gmail AI Triage Bota (limit: {pocet_zprav}, jen nepřečtené: {jen_neprectene}) ===")
    try:
        service = pripoj_gmail()
        konfig = nacti_konfiguraci()

        odpoved_stitky = service.users().labels().list(userId="me").execute()
        existujici_stitky = {s["name"]: s["id"] for s in odpoved_stitky.get("labels", [])}

        id_zpracovano = ziskej_nebo_vytvor_stitek(service, "AI/Zpracovano", existujici_stitky, "Šedá")

        dotaz = "in:inbox -label:AI/Zpracovano"
        if jen_neprectene:
            dotaz += " is:unread"

        vysledky = service.users().messages().list(
            userId="me",
            q=dotaz,
            maxResults=pocet_zprav
        ).execute()
        zpravy = vysledky.get("messages", [])

        if not zpravy:
            logging.info("Žádné nové zprávy ke zpracování.")
            return 0

        celkem = len(zpravy)
        logging.info(f"Nalezeno {celkem} zpráv. Spouštím paralelní AI analýzu...")

        hotovo = 0
        nove_zaznamy = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            budouci_vysledky = {executor.submit(zpracuj_jednu_zpravu, z["id"]): z["id"] for z in zpravy}

            for future in as_completed(budouci_vysledky):
                msg_id, odesilatel, predmet, prilohy, analyza = future.result()

                nazev_kategorie = f"AI/{analyza.kategorie}"
                barva_kategorie = konfig.get("kategorie", {}).get(analyza.kategorie, {}).get("barva", "Šedá")
                id_kategorie = ziskej_nebo_vytvor_stitek(service, nazev_kategorie, existujici_stitky, barva_kategorie)

                pridat_stitky = [id_kategorie, id_zpracovano]
                odebrat_stitky = []

                if analyza.priorita.value == "P1_URGENT":
                    id_urgent = ziskej_nebo_vytvor_stitek(service, "AI/P1-URGENT", existujici_stitky, "Červená")
                    pridat_stitky.append(id_urgent)

                if analyza.archivovat_z_inboxu:
                    odebrat_stitky.append("INBOX")

                service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={
                        "addLabelIds": pridat_stitky,
                        "removeLabelIds": odebrat_stitky
                    }
                ).execute()

                nove_zaznamy.append({
                    "id": msg_id,
                    "cas": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "priorita": analyza.priorita.value,
                    "kategorie": analyza.kategorie,
                    "odesilatel": odesilatel,
                    "predmet": predmet,
                    "prilohy": ", ".join(prilohy) if prilohy else "",
                    "shrnuti": analyza.shrnuti,
                    "archivovano": analyza.archivovat_z_inboxu,
                    "gmail_url": f"https://mail.google.com/mail/u/0/#all/{msg_id}"
                })

                hotovo += 1
                logging.info(f"[{hotovo}/{celkem}] '{predmet[:40]}' -> {analyza.priorita.value} | {nazev_kategorie}")
                
                if progress_callback:
                    progress_callback(hotovo, celkem, predmet)

        uloz_do_historie(nove_zaznamy)
        return hotovo

    except Exception as e:
        logging.error(f"Kritická chyba při běhu bota: {e}", exc_info=True)
        raise e

if __name__ == "__main__":
    spust_trideni(pocet_zprav=15)