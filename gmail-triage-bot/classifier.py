import os
import json
import time
from enum import Enum
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

MODELY_FALLBACK = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-4-argon",
]

def get_genai_client() -> genai.Client:
    load_dotenv("../.env", override=True)
    return genai.Client()

def nacti_konfiguraci() -> dict:
    with open("config.json", "r", encoding="utf-8-sig") as f:
        return json.load(f)

class Priorita(str, Enum):
    URGENT = "P1_URGENT"
    STANDARD = "P2_STANDARD"
    LOW = "P3_LOW"

class EmailAnalyza(BaseModel):
    priorita: Priorita = Field(description="Naléhavost vyřízení e-mailu: P1_URGENT (hoří/VIP/reklamace), P2_STANDARD (běžná agenda), P3_LOW (informativní/spam)")
    kategorie: str = Field(description="Přesný název kategorie vybraný ze seznamu povolených kategorií v zadání")
    shrnuti: str = Field(description="Maximálně 1 věcná věta shrnující o co jde a jaká akce se očekává")
    archivovat_z_inboxu: bool = Field(description="True pouze pokud jde o kategorii nastavenou k archivaci nebo čistě informační mail bez nutnosti akce")

def analyzuj_email(odesilatel: str, predmet: str, obsah: str, ma_prilohu: bool = False) -> EmailAnalyza:
    client = get_genai_client()
    konfig = nacti_konfiguraci()
    kategorie_dict = konfig.get("kategorie", {})
    povolene_nazvy = list(kategorie_dict.keys())
    
    if not povolene_nazvy:
        povolene_nazvy = ["Ostatni"]
        popis_kategorii = "- Ostatni (archivovat: False): Veškerá příchozí pošta"
    else:
        popis_kategorii = "\n".join(
            [f"- {nazev} (archivovat: {info.get('archivovat', False)}): {info['popis']}" for nazev, info in kategorie_dict.items()]
        )
        
    vip_seznam = ", ".join(konfig.get("vip_odesilatele", []))

    prompt = f"""
    Jsi AI asistent pro organizaci pošty ve firmě: {konfig.get('firma_popis') or 'Obchodní firma'}.
    Roztřiď příchozí e-mail podle těchto firemních pravidel.

    POVOLENÉ KATEGORIE (musíš vybrat PŘESNĚ jeden z těchto názvů):
    {popis_kategorii}

    VIP ODESÍLATELÉ (e-maily od nich mají VŽDY prioritu P1_URGENT a nesmí se archivovat):
    {vip_seznam if vip_seznam else "Žádní"}

    E-MAIL K ANALÝZE:
    Odesílatel: {odesilatel}
    Předmět: {predmet}
    Obsahuje přílohu: {"ANO" if ma_prilohu else "NE"}
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
            vysledek = EmailAnalyza.model_validate_json(response.text)
            
            if vysledek.kategorie not in povolene_nazvy:
                vysledek.kategorie = povolene_nazvy[0]
                
            if any(vip.lower() in odesilatel.lower() for vip in konfig.get("vip_odesilatele", []) if vip.strip()):
                vysledek.priorita = Priorita.URGENT
                vysledek.archivovat_z_inboxu = False

            return vysledek
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                posledni_chyba = e
                if "limit: 0" not in err_str and "PerDay" not in err_str:
                    time.sleep(12)
                continue
            if "503" in err_str or "UNAVAILABLE" in err_str:
                posledni_chyba = e
                time.sleep(2)
                continue
            raise e

    raise RuntimeError(f"Všechny modely jsou momentálně přetížené: {posledni_chyba}")