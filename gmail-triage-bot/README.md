# Gmail AI Triage Bot

Automatizovaný nástroj pro třídění, prioritizaci a organizaci příchozí pošty v Gmailu pomocí Google Gemini API a Gmail API.

## Řešený byznysový problém
Manažeři a majitelé e-shopů tráví hodiny týdně ručním probíráním e-mailové schránky, kde urgentní reklamace či faktury zapadají mezi informační zprávy a newslettery. Tento bot na pozadí automaticky vyhodnotí obsah každého nového e-mailu, určí jeho naléhavost a roztřídí ho do přehledných štítků v Gmailu.

## Klíčové funkce
- **Strukturovaná AI analýza (Pydantic + Gemini):** Vynucený JSON výstup zaručuje spolehlivou klasifikaci priority (`P1_URGENT`, `P2_STANDARD`, `P3_LOW`), kategorie a jednořádkového shrnutí.
- **Odolnost proti výpadkům (Model Fallback):** Automatické přepínání mezi modely (od rychlého `flash-lite` po záložní modely) při přetížení API (`503 UNAVAILABLE`).
- **Bezpečná práce se schránkou:** Bot nikdy e-maily nemaže. Pouze zakládá vnořené štítky (`AI/...`), označuje zpracované zprávy (`AI/Zpracovano`) proti duplicitnímu zpracování a nízko-prioritní balast archivuje z hlavního Inboxu.

## Struktura projektu
- `classifier.py` – AI jádro s definicí datových schémat (Pydantic) a fallback logikou.
- `gmail_connect.py` – OAuth 2.0 autentizace a připojení ke Gmail API.
- `triage_bot.py` – Hlavní orchestrátor propojující čtení e-mailů, AI klasifikaci a úpravu štítků v Gmailu.

## Spuštění
1. Vložte svůj `GEMINI_API_KEY` do souboru `.env` a OAuth přístupové údaje do `credentials.json`.
2. Nainstalujte závislosti (`google-genai`, `pydantic`, `python-dotenv`, `google-api-python-client`, `google-auth-oauthlib`, `truststore`).
3. Spusťte `python triage_bot.py`.
