import truststore
truststore.inject_into_ssl()

import base64
from gmail_connect import pripoj_gmail
from classifier import analyzuj_email

# Pomocná funkce pro získání nebo automatické vytvoření štítku v Gmailu
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
    print(f"[Nový štítek v Gmailu vytvořen: {nazev_stitku}]")
    return novy_stitek["id"]

# Pomocná funkce pro vytažení čitelného textu z těla e-mailu
def vytahni_text_emailu(payload: dict) -> str:
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
            # Rekurzivní průchod vnořenými částmi
            vysledek = vytahni_text_emailu(part)
            if vysledek:
                return vysledek
    elif payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    return ""

def spust_trideni(pocet_zprav: int = 5):
    service = pripoj_gmail()

    # 1. Načteme seznam všech aktuálních štítků v tvém Gmailu
    odpoved_stitky = service.users().labels().list(userId="me").execute()
    existujici_stitky = {s["name"]: s["id"] for s in odpoved_stitky.get("labels", [])}

    # Zajistíme existenci kontrolního štítku, abychom maily neřešili dokola
    id_zpracovano = ziskej_nebo_vytvor_stitek(service, "AI/Zpracovano", existujici_stitky)

    # 2. Najdeme zprávy v Inboxu, které ještě NEMŮJ štítek AI/Zpracovano
    vysledky = service.users().messages().list(
        userId="me",
        q="in:inbox -label:AI/Zpracovano",
        maxResults=pocet_zprav
    ).execute()
    zpravy = vysledky.get("messages", [])

    if not zpravy:
        print("Všechny e-maily v Inboxu jsou už roztříděné!")
        return

    print(f"Nalezeno {len(zpravy)} neroztříděných e-mailů. Spouštím AI analýzu...\n")

    for zprava in zpravy:
        msg_id = zprava["id"]
        detail = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        
        hlavicky = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        odesilatel = hlavicky.get("From", "Neznámý odesílatel")
        predmet = hlavicky.get("Subject", "(Bez předmětu)")
        
        # Vezmeme text e-mailu (ořízneme na prvních 2500 znaků kvůli rychlosti a ceně) nebo snippet
        text_tela = vytahni_text_emailu(detail["payload"]).strip()
        if not text_tela:
            text_tela = detail.get("snippet", "")
        text_tela = text_tela[:2500]

        print(f"Zpracovávám: {predmet[:55]}...")
        
        # 3. Pošleme e-mail do našeho AI klasifikátoru
        analyza = analyzuj_email(odesilatel, predmet, text_tela)

        # 4. Připravíme štítky, které se mají v Gmailu přidat a odebrat
        nazev_kategorie = f"AI/{analyza.kategorie.value}"
        id_kategorie = ziskej_nebo_vytvor_stitek(service, nazev_kategorie, existujici_stitky)

        pridat_stitky = [id_kategorie, id_zpracovano]
        odebrat_stitky = []

        # Pokud je to P1_URGENT, přidáme i výrazný prioritní štítek
        if analyza.priorita.value == "P1_URGENT":
            id_urgent = ziskej_nebo_vytvor_stitek(service, "AI/P1-URGENT", existujici_stitky)
            pridat_stitky.append(id_urgent)

        # Pokud AI vyhodnotí mail jako čistý newsletter/balast, uklidíme ho z Inboxu do archivu
        if analyza.archivovat_z_inboxu:
            odebrat_stitky.append("INBOX")

        # 5. Provedeme změnu přímo v Gmailu
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={
                "addLabelIds": pridat_stitky,
                "removeLabelIds": odebrat_stitky
            }
        ).execute()

        print(f"  -> Priorita: {analyza.priorita.value} | Štítek: {nazev_kategorie} | Archivováno: {analyza.archivovat_z_inboxu}")
        print(f"  -> Shrnutí:  {analyza.shrnuti}\n")

if __name__ == "__main__":
    # Pro první ostrý test zpracujeme maximálně 5 e-mailů
    spust_trideni(pocet_zprav=5)