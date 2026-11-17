import os
import logging
import base64
import truststore

truststore.inject_into_ssl()

# Zajistí, že skript vždy běží ze své vlastní složky (klíčové pro Plánovač úloh)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from gmail_connect import pripoj_gmail
from classifier import analyzuj_email

# Nastavení logování do souboru bot.log i do konzole
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def ziskej_nebo_vytvor_stitek(service, nazev_stitku: str, existujici_stitky: dict) -> str:
    if nazev_stitku in existujici_stitky:
        return existujici_stitky[nazev_stitku]

    novy_stitek = service.users().labels().create(
        userId="me",
        body={
            "name": nazev_stitku,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }
    ).execute()
    existujici_stitky[nazev_stitku] = novy_stitek["id"]
    logging.info(f"Nový štítek v Gmailu vytvořen: {nazev_stitku}")
    return novy_stitek["id"]

def vytahni_text_emailu(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
            vysledek = vytahni_text_emailu(part)
            if vysledek:
                return vysledek
    elif payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    return ""

def spust_trideni(pocet_zprav: int = 15):
    logging.info("=== Spouštím Gmail AI Triage Bota ===")
    try:
        service = pripoj_gmail()

        odpoved_stitky = service.users().labels().list(userId="me").execute()
        existujici_stitky = {s["name"]: s["id"] for s in odpoved_stitky.get("labels", [])}

        id_zpracovano = ziskej_nebo_vytvor_stitek(service, "AI/Zpracovano", existujici_stitky)

        vysledky = service.users().messages().list(
            userId="me",
            q="in:inbox -label:AI/Zpracovano",
            maxResults=pocet_zprav
        ).execute()
        zpravy = vysledky.get("messages", [])

        if not zpravy:
            logging.info("Žádné nové nepřečtené/neroztříděné zprávy v Inboxu.")
            return

        logging.info(f"Nalezeno {len(zpravy)} neroztříděných e-mailů.")

        for zprava in zpravy:
            msg_id = zprava["id"]
            detail = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

            hlavicky = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            odesilatel = hlavicky.get("From", "Neznámý odesílatel")
            predmet = hlavicky.get("Subject", "(Bez předmětu)")

            text_tela = vytahni_text_emailu(detail["payload"]).strip()
            if not text_tela:
                text_tela = detail.get("snippet", "")
            text_tela = text_tela[:2500]

            analyza = analyzuj_email(odesilatel, predmet, text_tela)

            nazev_kategorie = f"AI/{analyza.kategorie.value}"
            id_kategorie = ziskej_nebo_vytvor_stitek(service, nazev_kategorie, existujici_stitky)

            pridat_stitky = [id_kategorie, id_zpracovano]
            odebrat_stitky = []

            if analyza.priorita.value == "P1_URGENT":
                id_urgent = ziskej_nebo_vytvor_stitek(service, "AI/P1-URGENT", existujici_stitky)
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

            logging.info(f"Zpracováno: '{predmet[:45]}' -> {analyza.priorita.value} | {nazev_kategorie} | Archiv: {analyza.archivovat_z_inboxu}")

    except Exception as e:
        logging.error(f"Kritická chyba při běhu bota: {e}", exc_info=True)

if __name__ == "__main__":
    spust_trideni(pocet_zprav=15)
