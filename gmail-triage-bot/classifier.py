import os
import time
from enum import Enum
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Načte .env z nadřazené složky ai-retail-lab
load_dotenv("../.env", override=True)
client = genai.Client()

# Seznam modelů seřazený od nejrychlejšího po záložní (ochrana proti výpadkům 503)
MODELY_FALLBACK = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-4-argon",
]

# Definujeme pevné možnosti, ze kterých si AI MUSÍ vybrat
class Priorita(str, Enum):
    URGENT = "P1_URGENT"
    STANDARD = "P2_STANDARD"
    LOW = "P3_LOW"

class Kategorie(str, Enum):
    FAKTURY = "Faktury_Finance"
    ZAKAZNICI = "Zakaznici_Reklamace"
    DODAVATELE = "Dodavatele_Logistika"
    INTERNI = "Interni_Provoz"
    NEWSLETTER = "Newsletter_Spam"
    SYSTEM = "System_Notifikace"

# Definujeme přesnou strukturu výstupu
class EmailAnalyza(BaseModel):
    priorita: Priorita = Field(description="Naléhavost vyřízení e-mailu")
    kategorie: Kategorie = Field(description="Hlavní téma e-mailu pro roztřídění do složky")
    shrnuti: str = Field(description="Maximálně 1 krátká věta shrnující o co jde a co je potřeba udělat")
    archivovat_z_inboxu: bool = Field(description="True pouze pokud jde o newsletter, reklamu nebo čistě informační mail bez nutnosti akce")

def analyzuj_email(odesilatel: str, predmet: str, obsah: str) -> EmailAnalyza:
    prompt = f"""
    Jsi asistent manažera retailového provozu / e-shopu. Roztřiď následující příchozí e-mail.
    
    Odesílatel: {odesilatel}
    Předmět: {predmet}
    Obsah:
    {obsah}
    """

    posledni_chyba = None
    for model_name in MODELY_FALLBACK:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EmailAnalyza,
                    temperature=0.1,
                ),
            )
            print(f"[OK - použito {model_name}]")
            return EmailAnalyza.model_validate_json(response.text)
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                print(f"[Přetíženo: {model_name}, zkouším záložní model...]")
                posledni_chyba = e
                time.sleep(1)
                continue
            raise e

    raise RuntimeError(f"Všechny modely jsou momentálně přetížené: {posledni_chyba}")

# Testovací blok se 3 reálnými scénáři z praxe
if __name__ == "__main__":
    testovaci_emaily = [
        {
            "odesilatel": "novak@zakaznik.cz",
            "predmet": "Zničené zboží v zásilce č. 44910!",
            "obsah": "Dobrý den, dnes mi přišel balík a krabice byla úplně promáčená, kolo uvnitř je odřené. Potřebuji to okamžitě vyřešit, zítra odjíždíme na závody!"
        },
        {
            "odesilatel": "fakturace@velkoobchod-sport.cz",
            "predmet": "Faktura č. 20260891 - splatnost 14 dní",
            "obsah": "V příloze zasíláme daňový doklad za závoz zboží ze dne 15.11. Částka k úhradě: 48 500 Kč."
        },
        {
            "odesilatel": "novinky@slevy-kazdy-den.cz",
            "predmet": "🔥 Black Friday slevy až 70 % jen dnes!",
            "obsah": "Nenechte si ujít jedinečnou nabídku na zimní bundy a doplňky. Klikněte zde pro zobrazení katalogu."
        }
    ]

    for mail in testovaci_emaily:
        vysledek = analyzuj_email(mail["odesilatel"], mail["predmet"], mail["obsah"])
        print(f"\n--- E-MAIL: {mail['predmet']} ---")
        print(f"Priorita:   {vysledek.priorita.value}")
        print(f"Štítek:     {vysledek.kategorie.value}")
        print(f"Archivovat: {vysledek.archivovat_z_inboxu}")
        print(f"Shrnutí:    {vysledek.shrnuti}")