import os

import subprocess

def _zajistit_automaticke_trideni():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pythonw = os.path.abspath(os.path.join(base_dir, "..", ".venv", "Scripts", "pythonw.exe"))
        script = os.path.join(base_dir, "triage_bot.py")
        if os.path.exists(pythonw) and os.path.exists(script):
            subprocess.run(
                [
                    "schtasks", "/create", "/tn", "InboxAI_Trideni",
                    "/tr", f'"{pythonw}" "{script}"',
                    "/sc", "minute", "/mo", "30", "/f"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
    except Exception:
        pass

_zajistit_automaticke_trideni()
import json
import hashlib
import truststore
truststore.inject_into_ssl()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

CONFIG_FILE = "config.json"
ENV_FILE = "../.env"
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

COLOR_SLUGS = {
    "Šedá": "seda",
    "Světle modrá": "svetle_modra",
    "Tyrkysová": "tyrkysova",
    "Fialová": "fialova",
    "Růžová": "ruzova",
    "Červená": "cervena",
    "Tmavě šedá": "tmave_seda",
    "Modrá": "modra",
    "Petrolejová": "petrolejova",
    "Oranžová": "oranzova",
    "Žlutá": "zluta",
    "Zelená": "zelena",
}

st.set_page_config(
    page_title="InboxAI | Firemní správa pošty",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# KONTROLA PRVNÍHO SPUŠTĚNÍ (ONBOARDING)
# ---------------------------------------------------------
def zkontroluj_instalaci():
    chybi_env = not os.path.exists(ENV_FILE)
    chybi_cred = not os.path.exists(CREDENTIALS_FILE)
    return chybi_env or chybi_cred

if zkontroluj_instalaci():
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0; margin-bottom: 2rem;'>
        <h1 style='font-size: 2.5rem; color: #0F172A; margin-bottom: 0.5rem;'>Vítejte v InboxAI 👋</h1>
        <p style='color: #64748B; font-size: 1.1rem;'>Pro první spuštění potřebujeme propojit aplikaci s vaším Google účtem.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("1. Vložte Gemini API klíč")
            st.caption("Slouží pro přístup k umělé inteligenci (získáte v Google AI Studio).")
            gemini_key = st.text_input("Gemini API Key:", type="password", placeholder="AIzaSy...")
            
            st.divider()
            
            st.subheader("2. Přístup k firemní poště")
            st.caption("Nahrajte soubor `credentials.json` (získáte v Google Cloud Console).")
            uploaded_cred = st.file_uploader("Nahrát credentials.json", type=["json"])
            
            st.write("")
            if st.button("Dokončit instalaci a spustit aplikaci", type="primary", use_container_width=True):
                if not gemini_key:
                    st.error("Chybí Gemini API klíč.")
                elif not uploaded_cred:
                    st.error("Chybí soubor credentials.json.")
                else:
                    with open(ENV_FILE, "w", encoding="utf-8") as f:
                        f.write(f"GEMINI_API_KEY={gemini_key.strip()}\n")
                    
                    with open(CREDENTIALS_FILE, "wb") as f:
                        f.write(uploaded_cred.getvalue())
                        
                    st.success("Úspěšně nastaveno! Aplikace se nyní restartuje...")
                    st.rerun()
    st.stop()

import importlib, triage_bot
importlib.reload(triage_bot)
from triage_bot import spust_trideni, synchronizuj_barvy_stitku, GMAIL_BARVY, HISTORY_FILE

circle_css_rules = []
for c_name, c_hex in GMAIL_BARVY.items():
    slug = COLOR_SLUGS[c_name]
    circle_css_rules.append(f"""
    div[class*="st-key-cpick_"][class*="_{slug}"] button {{
        background-color: {c_hex["backgroundColor"]} !important;
        color: {c_hex["textColor"]} !important;
        border-radius: 50% !important;
        width: 28px !important;
        height: 28px !important;
        min-height: 28px !important;
        max-width: 28px !important;
        padding: 0 !important;
        margin: 2px auto !important;
        border: 1px solid rgba(0, 0, 0, 0.12) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.12s ease, box-shadow 0.12s ease !important;
    }}
    div[class*="st-key-cpick_"][class*="_{slug}"] button:hover {{
        transform: scale(1.15) !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important;
    }}
    """)

st.markdown(f"""
<style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    .block-container {{
        padding-top: 1.75rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }}

    .header-card {{
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.35rem 1.85rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .header-title {{
        font-size: 1.55rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
        letter-spacing: -0.02em;
    }}
    .header-sub {{
        color: #475569;
        font-size: 0.92rem;
        margin-top: 0.2rem;
    }}
    .status-pill {{
        background-color: #ECFDF5;
        color: #059669;
        border: 1px solid #A7F3D0;
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        white-space: nowrap;
    }}

    .metric-box {{
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.1rem 1.35rem;
        height: 102px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }}
    .metric-title {{
        color: #64748B;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .metric-num {{
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.1;
    }}
    .num-red {{ color: #DC2626; }}
    .num-blue {{ color: #2563EB; }}

    .label-preview {{
        display: inline-flex;
        align-items: center;
        padding: 0.32rem 0.75rem;
        border-radius: 6px;
        font-size: 0.84rem;
        font-weight: 600;
        line-height: 1.2;
        white-space: nowrap;
    }}
    .table-header {{
        color: #64748B;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 0 0.5rem 0.35rem 0.5rem;
    }}

    /* Stavová navigace ve stylu záložek */
    div[class*="st-key-nav_tabs"] div[role="radiogroup"] {{
        flex-direction: row !important;
        gap: 1.75rem !important;
        border-bottom: 1px solid #E2E8F0 !important;
        padding-bottom: 0 !important;
        margin-bottom: 1rem !important;
    }}
    div[class*="st-key-nav_tabs"] div[role="radiogroup"] label {{
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        padding: 0.45rem 0.2rem 0.65rem 0.2rem !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: color 0.15s ease, border-color 0.15s ease !important;
    }}
    div[class*="st-key-nav_tabs"] div[role="radiogroup"] label > div:first-child {{
        display: none !important;
    }}
    div[class*="st-key-nav_tabs"] div[role="radiogroup"] label p {{
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        color: #475569 !important;
    }}
    div[class*="st-key-nav_tabs"] div[role="radiogroup"] label:hover p {{
        color: #0F172A !important;
    }}
    div[class*="st-key-nav_tabs"] div[role="radiogroup"] label:has(input:checked) {{
        border-bottom: 2px solid #2563EB !important;
    }}
    div[class*="st-key-nav_tabs"] div[role="radiogroup"] label:has(input:checked) p {{
        color: #2563EB !important;
        font-weight: 600 !important;
    }}

    [data-testid="stPopoverBody"] {{
        min-width: 245px !important;
        padding: 0.75rem !important;
    }}

    [data-testid="stSidebar"] {{
        border-right: 1px solid #E2E8F0;
    }}

    {"".join(circle_css_rules)}
</style>
""", unsafe_allow_html=True)

def nacti_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {"firma_popis": "", "vip_odesilatele": [], "kategorie": {}}
    with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def uloz_config(data: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def nacti_historii() -> list:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def resetuj_trideni() -> int:
    upraveno_zprav = 0
    if os.path.exists(TOKEN_FILE):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(TOKEN_FILE)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w", encoding="utf-8") as tf:
                    tf.write(creds.to_json())

            service = build("gmail", "v1", credentials=creds)
            labels_resp = service.users().labels().list(userId="me").execute()
            vsechny_stitky = labels_resp.get("labels", [])
            konfig_kategorie = set(nacti_config().get("kategorie", {}).keys())
            systemove_stitky = {"URGENTNÍ", "Zpracovano AI", "P1-URGENT", "Zpracovano (AI)", "P1-URGENT (AI)", "AI"}
            ai_stitky = [
                lbl for lbl in vsechny_stitky
                if lbl.get("name") in konfig_kategorie
                or lbl.get("name") in systemove_stitky
                or lbl.get("name", "").startswith("AI/")
                or lbl.get("name", "").endswith(" (AI)")
            ]
            ai_label_ids = [lbl["id"] for lbl in ai_stitky]

            if ai_label_ids:
                zpravy_k_resetu = set()
                for lbl_id in ai_label_ids:
                    page_token = None
                    while True:
                        res = service.users().messages().list(
                            userId="me",
                            labelIds=[lbl_id],
                            pageToken=page_token,
                            maxResults=500
                        ).execute()
                        for m in res.get("messages", []):
                            zpravy_k_resetu.add(m["id"])
                        page_token = res.get("nextPageToken")
                        if not page_token:
                            break

                seznam_ids = list(zpravy_k_resetu)
                upraveno_zprav = len(seznam_ids)
                for i in range(0, len(seznam_ids), 1000):
                    davka = seznam_ids[i:i + 1000]
                    service.users().messages().batchModify(
                        userId="me",
                        body={
                            "ids": davka,
                            "removeLabelIds": ai_label_ids,
                            "addLabelIds": ["INBOX"]
                        }
                    ).execute()

                for lbl in sorted(ai_stitky, key=lambda x: len(x.get("name", "")), reverse=True):
                    try:
                        service.users().labels().delete(userId="me", id=lbl["id"]).execute()
                    except Exception:
                        pass
        except Exception as e:
            st.error(f"Chyba při čištění štítků v Gmailu: {e}")

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

    if os.path.exists("bot.log"):
        with open("bot.log", "a", encoding="utf-8") as f:
            f.write("[INFO] Uživatel provedl reset třídění, smazání štítků a historie.\n")

    return upraveno_zprav

def get_safe_id(klic_id: str) -> str:
    return hashlib.md5(klic_id.encode("utf-8")).hexdigest()[:8]

def priprav_stav_barvy(klic_id: str, vychozi_barva: str) -> str:
    safe_id = get_safe_id(klic_id)
    state_key = f"sel_color_{safe_id}"
    ver_key = f"pop_ver_{safe_id}"

    if state_key not in st.session_state:
        st.session_state[state_key] = vychozi_barva if vychozi_barva in GMAIL_BARVY else "Šedá"
    if ver_key not in st.session_state:
        st.session_state[ver_key] = 0

    aktualni = st.session_state[state_key]
    barva_hex = GMAIL_BARVY.get(aktualni, GMAIL_BARVY["Šedá"])

    return f"""
    div[class*="st-key-pop_{safe_id}_"] {{
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }}
    div[class*="st-key-pop_{safe_id}_"] > div {{
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }}
    div[class*="st-key-pop_{safe_id}_"] button {{
        background-color: {barva_hex["backgroundColor"]} !important;
        border-radius: 50% !important;
        width: 30px !important;
        height: 30px !important;
        min-width: 30px !important;
        min-height: 30px !important;
        max-width: 30px !important;
        max-height: 30px !important;
        padding: 0 !important;
        margin: 0 auto !important;
        border: 2px solid rgba(15, 23, 42, 0.16) !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.12s ease, box-shadow 0.12s ease !important;
    }}
    div[class*="st-key-pop_{safe_id}_"] button:hover {{
        transform: scale(1.12) !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.22) !important;
    }}
    div[class*="st-key-pop_{safe_id}_"] button * {{
        display: none !important;
    }}
    """

def vykresli_vyber_barvy(klic_id: str) -> str:
    safe_id = get_safe_id(klic_id)
    state_key = f"sel_color_{safe_id}"
    ver_key = f"pop_ver_{safe_id}"

    aktualni = st.session_state[state_key]
    barvy_seznam = list(GMAIL_BARVY.keys())

    with st.popover(" ", key=f"pop_{safe_id}_{st.session_state[ver_key]}", help=f"Barva štítku: {aktualni}"):
        st.caption(f"Vybráno: **{aktualni}**")
        for radek_idx in range(2):
            cols = st.columns(6, gap="small")
            for col_idx in range(6):
                b_nazev = barvy_seznam[radek_idx * 6 + col_idx]
                slug = COLOR_SLUGS[b_nazev]
                with cols[col_idx]:
                    if st.button("a", key=f"cpick_{safe_id}_{slug}", help=b_nazev):
                        st.session_state[state_key] = b_nazev
                        st.session_state[ver_key] += 1
                        st.rerun()

    return st.session_state[state_key]

konfig_aktualni = nacti_config()
ma_stitky = len(konfig_aktualni.get("kategorie", {})) > 0

st.markdown("""
<div class="header-card">
    <div>
        <div class="header-title">InboxAI — Správa a prioritizace pošty</div>
        <div class="header-sub">Automatické třídění agendy, detekce příloh a barevná organizace štítků v Gmailu</div>
    </div>
    <div class="status-pill">● Aktivní (Gemini Flash)</div>
</div>
""", unsafe_allow_html=True)

if not ma_stitky:
    st.warning("👋 **Začínáme:** Přejděte do záložky **Nastavení kategorií a barev** a vytvořte si první firemní štítky, podle kterých má AI poštu třídit.")

with st.sidebar:
    st.markdown("### Rychlé třídění")
    pocet_mailu = st.slider("Počet zpráv ke zpracování", min_value=5, max_value=50, value=15)
    jen_neprectene = st.checkbox("Pouze nepřečtené e-maily", value=False)
    
    if st.button("Spustit třídění Inboxu", type="primary", use_container_width=True, disabled=not ma_stitky):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def aktualizuj_stav(hotovo, celkem, predmet):
            progress_bar.progress(hotovo / celkem)
            status_text.caption(f"Zpracováno {hotovo}/{celkem}: {predmet[:32]}...")

        try:
            pocet = spust_trideni(
                pocet_zprav=pocet_mailu,
                jen_neprectene=jen_neprectene,
                progress_callback=aktualizuj_stav
            )
            st.session_state["nav_tabs"] = "Přehled roztříděné pošty"
            st.toast(f"Hotovo! Zpracováno {pocet} e-mailů.", icon="✅")
            st.rerun()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "limit" in str(e).lower():
                st.error("⚠️ **Vyčerpán limit bezplatného tarifu Gemini API (429).** Počkejte na obnovení kvóty nebo v Google AI Studio zapněte fakturaci (Pay-as-you-go) pro neomezený provoz.")
            else:
                st.error(f"Chyba při třídění: {e}")

    if not ma_stitky:
        st.caption("Pro spuštění nejprve přidejte alespoň 1 štítek v Nastavení.")

    st.divider()
    st.markdown("### Počáteční úklid schránky")
    st.caption("Hromadné protřídění starší pošty při prvním nasazení na účet.")
    pocet_uklid = st.selectbox("Velikost dávky", options=[50, 100, 200, 300, 400, 500], index=0)
    
    if st.button("Spustit hromadný úklid", use_container_width=True, disabled=not ma_stitky):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def aktualizuj_uklid(hotovo, celkem, predmet):
            progress_bar.progress(hotovo / celkem)
            status_text.caption(f"Úklid {hotovo}/{celkem}: {predmet[:32]}...")

        try:
            pocet = spust_trideni(
                pocet_zprav=pocet_uklid,
                jen_neprectene=False,
                progress_callback=aktualizuj_uklid
            )
            st.session_state["nav_tabs"] = "Přehled roztříděné pošty"
            st.toast(f"Úklid dokončen ({pocet} zpráv).", icon="✅")
            st.rerun()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "limit" in str(e).lower():
                st.error("⚠️ **Vyčerpán limit bezplatného tarifu Gemini API (429).** Počkejte na obnovení kvóty nebo v Google AI Studio zapněte fakturaci (Pay-as-you-go) pro neomezený provoz.")
            else:
                st.error(f"Chyba při hromadném úklidu: {e}")

    st.divider()
    st.markdown("### Reset třídění")
    st.caption("Odebere štítky AI z e-mailů a smaže historii, abyste mohli poštu roztřídit znovu.")
    with st.popover("Resetovat třídění", use_container_width=True):
        st.warning("Tato akce odebere štítky **AI/...** ze všech zpráv v Gmailu, vrátí archivované e-maily zpět do doručené pošty a vymaže historii.")
        if st.button("Potvrdit a resetovat vše", type="primary", use_container_width=True, key="confirm_reset_btn"):
            with st.spinner("Resetuji štítky v Gmailu a mažu historii..."):
                pocet_reset = resetuj_trideni()
            st.toast(f"Třídění resetováno (očištěno {pocet_reset} zpráv).", icon="🔄")
            st.rerun()

historie = nacti_historii()
urgentni_zaznamy = [z for z in historie if z["priorita"] == "P1_URGENT"]
s_prilohou = [z for z in historie if z.get("prilohy")]
archivovane = [z for z in historie if z.get("archivovano")]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Urgentní</div>
        <div class="metric-num num-red">{len(urgentni_zaznamy)}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">S přílohou</div>
        <div class="metric-num num-blue">{len(s_prilohou)}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Uklizeno z Inboxu</div>
        <div class="metric-num">{len(archivovane)}</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Zpracováno celkem</div>
        <div class="metric-num">{len(historie)}</div>
    </div>""", unsafe_allow_html=True)

st.write("")

ZALOZKY = [
    "Přehled roztříděné pošty",
    "Nastavení kategorií a barev",
    "Záznam běhu (Log)"
]
if "nav_tabs" not in st.session_state:
    st.session_state["nav_tabs"] = ZALOZKY[0] if ma_stitky else ZALOZKY[1]

vybrana_zalozka = st.radio(
    "Navigace",
    options=ZALOZKY,
    horizontal=True,
    label_visibility="collapsed",
    key="nav_tabs"
)

if vybrana_zalozka == "Přehled roztříděné pošty":
    if not historie:
        if ma_stitky:
            st.info("Zatím zde nejsou žádné záznamy. Spusťte třídění v levém panelu.")
        else:
            st.info("Zatím nemáte nastavené žádné štítky. Začněte v záložce **Nastavení kategorií a barev**.")
    else:
        PRIORITA_NAZVY = {
            "P1_URGENT": "🔴 URGENTNÍ",
            "P2_STANDARD": "🟡 BĚŽNÉ",
            "P3_LOW": "⚪ INFORMAČNÍ"
        }
        dostupne_kat = sorted(list({z["kategorie"] for z in historie if z.get("kategorie")}))

        with st.container(border=True):
            col_s1, col_s2 = st.columns([3, 1.1], vertical_alignment="center")
            with col_s1:
                hledat_text = st.text_input(
                    "Hledat",
                    placeholder="🔍 Hledat podle odesílatele, předmětu nebo AI shrnutí...",
                    label_visibility="collapsed"
                )
            with col_s2:
                jen_s_prilohou = st.checkbox("📎 Pouze s přílohou", value=False)

            col_p1, col_p2 = st.columns([1.15, 1.85], gap="large")
            with col_p1:
                if hasattr(st, "pills"):
                    vybrane_prio = st.pills(
                        "Priorita (bez výběru = vše):",
                        options=["P1_URGENT", "P2_STANDARD", "P3_LOW"],
                        format_func=lambda x: PRIORITA_NAZVY.get(x, x),
                        selection_mode="multi",
                        key="pills_prio"
                    )
                else:
                    vybrane_prio = st.multiselect(
                        "Priorita:",
                        options=["P1_URGENT", "P2_STANDARD", "P3_LOW"],
                        format_func=lambda x: PRIORITA_NAZVY.get(x, x)
                    )
            with col_p2:
                if hasattr(st, "pills"):
                    vybrane_kat = st.pills(
                        "Kategorie (bez výběru = vše):",
                        options=dostupne_kat,
                        selection_mode="multi",
                        key="pills_kat"
                    )
                else:
                    vybrane_kat = st.multiselect("Kategorie:", options=dostupne_kat)

        aktivni_prio = vybrane_prio if vybrane_prio else ["P1_URGENT", "P2_STANDARD", "P3_LOW"]
        aktivni_kat = vybrane_kat if vybrane_kat else dostupne_kat
        dotaz_lower = hledat_text.strip().lower()

        PRIORITA_PORADI = {"P1_URGENT": 0, "P2_STANDARD": 1, "P3_LOW": 2}
        filtrovana_data = sorted(
            [
                z for z in historie
                if z.get("priorita") in aktivni_prio
                and z.get("kategorie") in aktivni_kat
                and (not jen_s_prilohou or bool(z.get("prilohy")))
                and (
                    not dotaz_lower
                    or dotaz_lower in (
                        f"{z.get('odesilatel', '')} {z.get('predmet', '')} {z.get('shrnuti', '')}"
                    ).lower()
                )
            ],
            key=lambda z: PRIORITA_PORADI.get(z.get("priorita"), 99)
        )

        st.caption(f"Zobrazeno zpráv: {len(filtrovana_data)}")
        
        if filtrovana_data:
            import html as _html
            kat_konfig = nacti_config().get("kategorie", {})

            st.markdown("""
            <style>
                .mail-card {
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-left-width: 5px;
                    border-radius: 10px;
                    padding: 0.9rem 1.2rem;
                    margin-bottom: 0.65rem;
                    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    gap: 1rem;
                }
                .mail-card:hover {
                    border-color: #CBD5E1;
                    box-shadow: 0 3px 8px rgba(15, 23, 42, 0.06);
                }
                .mail-main {
                    flex: 1;
                    min-width: 0;
                }
                .mail-meta {
                    display: flex;
                    flex-wrap: wrap;
                    align-items: center;
                    gap: 0.45rem;
                    margin-bottom: 0.4rem;
                }
                .prio-badge {
                    font-size: 0.74rem;
                    font-weight: 700;
                    padding: 0.16rem 0.55rem;
                    border-radius: 999px;
                    letter-spacing: 0.02em;
                }
                .kat-badge {
                    font-size: 0.76rem;
                    font-weight: 600;
                    padding: 0.16rem 0.6rem;
                    border-radius: 6px;
                }
                .mail-sender {
                    font-size: 0.85rem;
                    font-weight: 600;
                    color: #334155;
                    margin-left: 0.15rem;
                }
                .mail-attach {
                    font-size: 0.76rem;
                    color: #1D4ED8;
                    background-color: #EFF6FF;
                    border: 1px solid #BFDBFE;
                    padding: 0.12rem 0.5rem;
                    border-radius: 6px;
                }
                .mail-subject {
                    font-size: 1.0rem;
                    font-weight: 700;
                    color: #0F172A;
                    margin-bottom: 0.25rem;
                    line-height: 1.35;
                }
                .mail-summary {
                    font-size: 0.88rem;
                    color: #475569;
                    line-height: 1.45;
                }
                .mail-action a {
                    display: inline-block;
                    padding: 0.42rem 0.85rem;
                    background-color: #F8FAFC;
                    color: #1E293B !important;
                    border: 1px solid #CBD5E1;
                    border-radius: 7px;
                    font-size: 0.82rem;
                    font-weight: 600;
                    text-decoration: none !important;
                    white-space: nowrap;
                    transition: all 0.15s ease;
                }
                .mail-action a:hover {
                    background-color: #2563EB;
                    color: #FFFFFF !important;
                    border-color: #2563EB;
                }
            </style>
            """, unsafe_allow_html=True)

            karty_html = []
            for z in filtrovana_data:
                prio = z.get("priorita", "P2_STANDARD")
                if prio == "P1_URGENT":
                    border_col = "#DC2626"
                    prio_bg = "#FEF2F2"
                    prio_txt = "#DC2626"
                    prio_label = "🔴 URGENTNÍ"
                elif prio == "P2_STANDARD":
                    border_col = "#F59E0B"
                    prio_bg = "#FFFBEB"
                    prio_txt = "#B45309"
                    prio_label = "🟡 BĚŽNÉ"
                else:
                    border_col = "#94A3B8"
                    prio_bg = "#F1F5F9"
                    prio_txt = "#475569"
                    prio_label = "⚪ INFORMAČNÍ"

                kat_nazev = z.get("kategorie", "")
                barva_nazev = kat_konfig.get(kat_nazev, {}).get("barva", "Šedá")
                barva_hex = GMAIL_BARVY.get(barva_nazev, GMAIL_BARVY["Šedá"])

                odesilatel_cisty = _html.escape(z.get("odesilatel", "").split("<")[0].strip().strip('"'))
                predmet_cisty = _html.escape(z.get("predmet", "(Bez předmětu)"))
                shrnuti_ciste = _html.escape(z.get("shrnuti", ""))
                kat_cista = _html.escape(kat_nazev)
                url_cista = _html.escape(z.get("gmail_url", "#"), quote=True)

                priloha_html = ""
                if z.get("prilohy"):
                    priloha_html = f'<span class="mail-attach">📎 {_html.escape(str(z["prilohy"]))}</span>'

                karty_html.append(
                    f'<div class="mail-card" style="border-left-color: {border_col};">'
                    f'<div class="mail-main">'
                    f'<div class="mail-meta">'
                    f'<span class="prio-badge" style="background-color:{prio_bg}; color:{prio_txt};">{prio_label}</span>'
                    f'<span class="kat-badge" style="background-color:{barva_hex["backgroundColor"]}; color:{barva_hex["textColor"]};">{kat_cista}</span>'
                    f'<span class="mail-sender">{odesilatel_cisty}</span>'
                    f'{priloha_html}'
                    f'</div>'
                    f'<div class="mail-subject">{predmet_cisty}</div>'
                    f'<div class="mail-summary">{shrnuti_ciste}</div>'
                    f'</div>'
                    f'<div class="mail-action"><a href="{url_cista}" target="_blank">Otevřít v Gmailu ↗</a></div>'
                    f'</div>'
                )

            st.markdown("".join(karty_html), unsafe_allow_html=True)
        else:
            st.warning("Žádné zprávy neodpovídají zvolenému filtru.")

elif vybrana_zalozka == "Nastavení kategorií a barev":
    st.subheader("Firemní pravidla, štítky a barvy v Gmailu")
    st.caption("Vytvořte si vlastní štítky. Po uložení se automaticky založí a obarví přímo ve vašem Gmailu.")
    
    konfig = nacti_config()
    existujici_kategorie = konfig.get("kategorie", {})

    popover_styles = [priprav_stav_barvy("novy_stitek", "Zelená")]
    for nazev, info in existujici_kategorie.items():
        popover_styles.append(priprav_stav_barvy(nazev, info.get("barva", "Šedá")))
    st.markdown(f"<style>{''.join(popover_styles)}</style>", unsafe_allow_html=True)
    
    with st.container(border=True):
        col_firm1, col_firm2 = st.columns(2, gap="large")
        with col_firm1:
            novy_popis_firmy = st.text_input(
                "Obor podnikání / kontext firmy:",
                value=konfig.get("firma_popis", ""),
                placeholder="Např. E-shop s elektronikou a servis"
            )
            st.caption("Slouží jako kontext pro AI při vyhodnocování naléhavosti e-mailů.")
        with col_firm2:
            vip_text = st.text_area(
                "VIP odesílatelé nebo domény (jeden na řádek — vždy priorita URGENTNÍ):",
                value="\n".join(konfig.get("vip_odesilatele", [])),
                placeholder="sef@dodavatel.cz\n@klicovy-klient.cz",
                height=90
            )

    st.write("")
    st.markdown("#### Vaše firemní štítky")
    
    upraveno_kategorie = {}
    smazat_klic = None

    if not existujici_kategorie:
        st.info("Zatím nemáte vytvořené žádné štítky. Vytvořte si první štítek ve formuláři níže.")
    else:
        h1, h2, h3, h4, h5 = st.columns([1.7, 3.0, 0.7, 0.9, 0.45])
        h1.markdown('<div class="table-header">Štítek v Gmailu</div>', unsafe_allow_html=True)
        h2.markdown('<div class="table-header">Pravidlo pro AI zařazení</div>', unsafe_allow_html=True)
        h3.markdown('<div class="table-header" style="text-align:center;">Barva</div>', unsafe_allow_html=True)
        h4.markdown('<div class="table-header">Archivace</div>', unsafe_allow_html=True)
        h5.markdown('<div class="table-header"></div>', unsafe_allow_html=True)

        for nazev, info in existujici_kategorie.items():
            with st.container(border=True):
                c_nazev, c_popis, c_barva, c_arch, c_del = st.columns([1.7, 3.0, 0.7, 0.9, 0.45], vertical_alignment="center")
                
                with c_barva:
                    vybrana_barva = vykresli_vyber_barvy(nazev)
                
                barva_hex = GMAIL_BARVY.get(vybrana_barva, GMAIL_BARVY["Šedá"])
                with c_nazev:
                    st.markdown(
                        f'<span class="label-preview" style="background-color:{barva_hex["backgroundColor"]}; color:{barva_hex["textColor"]};">{nazev}</span>',
                        unsafe_allow_html=True
                    )
                with c_popis:
                    novy_popis = st.text_input("Pravidlo", value=info["popis"], key=f"popis_{nazev}", label_visibility="collapsed")
                with c_arch:
                    nova_arch = st.checkbox("Archivovat", value=info.get("archivovat", False), key=f"arch_{nazev}")
                with c_del:
                    if st.button("🗑️", key=f"del_{nazev}", help=f"Smazat štítek {nazev}"):
                        smazat_klic = nazev
                    
                upraveno_kategorie[nazev] = {
                    "popis": novy_popis,
                    "archivovat": nova_arch,
                    "barva": vybrana_barva
                }

    if smazat_klic:
        del konfig["kategorie"][smazat_klic]
        uloz_config(konfig)
        st.toast(f"Štítek {smazat_klic} byl odstraněn.", icon="🗑️")
        st.rerun()

    st.write("")
    st.markdown("#### Přidat nový štítek")
    if "new_form_ver" not in st.session_state:
        st.session_state["new_form_ver"] = 0
    nf_ver = st.session_state["new_form_ver"]

    with st.container(border=True):
        c_new1, c_new2, c_new3, c_new4 = st.columns([1.8, 3.2, 0.7, 1.0], vertical_alignment="center")
        novy_nazev_kat = c_new1.text_input("Název", placeholder="Např. Faktury", key=f"new_kat_name_{nf_ver}", label_visibility="collapsed")
        novy_popis_kat = c_new2.text_input("Popis", placeholder="Jaké e-maily sem zařadit (např. daňové doklady a platby)...", key=f"new_kat_desc_{nf_ver}", label_visibility="collapsed")
        with c_new3:
            nova_barva_kat = vykresli_vyber_barvy("novy_stitek")
        with c_new4:
            novy_arch_kat = st.checkbox("Archivovat", key=f"new_arch_{nf_ver}")

    st.write("")
    if st.button("Uložit nastavení a propisovat barvy do Gmailu", type="primary"):
        konfig["firma_popis"] = novy_popis_firmy
        konfig["vip_odesilatele"] = [r.strip() for r in vip_text.splitlines() if r.strip()]
        konfig["kategorie"] = upraveno_kategorie
        
        if novy_nazev_kat.strip() and novy_popis_kat.strip():
            cisty_klic = " ".join(novy_nazev_kat.strip().replace("_", " ").split())
            konfig["kategorie"][cisty_klic] = {
                "popis": novy_popis_kat.strip(),
                "archivovat": novy_arch_kat,
                "barva": nova_barva_kat
            }
            st.session_state["new_form_ver"] += 1
            st.session_state[f"sel_color_{get_safe_id('novy_stitek')}"] = "Zelená"
            
        uloz_config(konfig)
        if konfig["kategorie"]:
            with st.spinner("Synchronizuji štítky a barvy přímo do Gmailu..."):
                synchronizuj_barvy_stitku()
        st.toast("Nastavení uloženo a barvy v Gmailu aktualizovány!", icon="✅")
        st.rerun()

elif vybrana_zalozka == "Záznam běhu (Log)":
    st.subheader("Záznam systémových operací")
    if os.path.exists("bot.log"):
        with open("bot.log", "r", encoding="utf-8") as f:
            radky = f.readlines()[-20:]
        st.code("".join(radky), language="text")
    else:
        st.info("Zatím neexistuje žádný log.")