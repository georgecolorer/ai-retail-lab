import os
import json
import base64
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
                    # Uložení .env
                    with open(ENV_FILE, "w", encoding="utf-8") as f:
                        f.write(f"GEMINI_API_KEY={gemini_key.strip()}\n")
                    
                    # Uložení credentials.json
                    with open(CREDENTIALS_FILE, "wb") as f:
                        f.write(uploaded_cred.getvalue())
                        
                    st.success("Úspěšně nastaveno! Aplikace se nyní restartuje...")
                    st.rerun()
    st.stop()

from triage_bot import spust_trideni, synchronizuj_barvy_stitku, GMAIL_BARVY, HISTORY_FILE

# Zbytek aplikace (CSS styly atd.) se načte až po úspěšném onboardingu
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

def vykresli_vyber_barvy(klic_id: str, vychozi_barva: str) -> str:
    state_key = f"sel_color_{klic_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = vychozi_barva if vychozi_barva in GMAIL_BARVY else "Šedá"

    aktualni = st.session_state[state_key]
    barvy_seznam = list(GMAIL_BARVY.keys())

    with st.popover("Barva", use_container_width=True):
        st.caption(f"Vybráno: **{aktualni}**")
        for radek_idx in range(2):
            cols = st.columns(6, gap="small")
            for col_idx in range(6):
                b_nazev = barvy_seznam[radek_idx * 6 + col_idx]
                slug = COLOR_SLUGS[b_nazev]
                with cols[col_idx]:
                    if st.button("a", key=f"cpick_{klic_id}_{slug}", help=b_nazev):
                        st.session_state[state_key] = b_nazev
                        st.rerun()

    return st.session_state[state_key]

st.markdown("""
<div class="header-card">
    <div>
        <div class="header-title">InboxAI — Správa a prioritizace pošty</div>
        <div class="header-sub">Automatické třídění agendy, detekce příloh a barevná organizace štítků v Gmailu</div>
    </div>
    <div class="status-pill">● Aktivní (Gemini Flash)</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Rychlé třídění")
    pocet_mailu = st.slider("Počet zpráv ke zpracování", min_value=5, max_value=50, value=25)
    jen_neprectene = st.checkbox("Pouze nepřečtené e-maily", value=False)
    
    if st.button("Spustit třídění Inboxu", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def aktualizuj_stav(hotovo, celkem, predmet):
            progress_bar.progress(hotovo / celkem)
            status_text.caption(f"Zpracováno {hotovo}/{celkem}: {predmet[:32]}...")

        # Pokud chybí token, aplikace si ho při prvním spuštění vyžádá sama
        pocet = spust_trideni(
            pocet_zprav=pocet_mailu,
            jen_neprectene=jen_neprectene,
            progress_callback=aktualizuj_stav
        )
        st.toast(f"Hotovo! Zpracováno {pocet} e-mailů.", icon="✅")
        st.rerun()

    st.divider()
    st.markdown("### Počáteční úklid schránky")
    st.caption("Hromadné protřídění starší pošty při prvním nasazení na účet.")
    pocet_uklid = st.selectbox("Velikost dávky", options=[50, 100, 200, 300, 400, 500], index=0)
    
    if st.button("Spustit hromadný úklid", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def aktualizuj_uklid(hotovo, celkem, predmet):
            progress_bar.progress(hotovo / celkem)
            status_text.caption(f"Úklid {hotovo}/{celkem}: {predmet[:32]}...")

        pocet = spust_trideni(
            pocet_zprav=pocet_uklid,
            jen_neprectene=False,
            progress_callback=aktualizuj_uklid
        )
        st.toast(f"Úklid dokončen ({pocet} zpráv).", icon="✅")
        st.rerun()

historie = nacti_historii()
urgentni_zaznamy = [z for z in historie if z["priorita"] == "P1_URGENT"]
s_prilohou = [z for z in historie if z.get("prilohy")]
archivovane = [z for z in historie if z.get("archivovano")]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-title">Urgentní (P1)</div>
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

tab_prehled, tab_nastaveni, tab_log = st.tabs([
    "Přehled roztříděné pošty",
    "Nastavení kategorií a barev",
    "Záznam běhu (Log)"
])

with tab_prehled:
    if not historie:
        st.info("Zatím zde nejsou žádné záznamy. Spusťte třídění v levém panelu.")
    else:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            filtr_priorita = st.multiselect(
                "Filtr priority:",
                options=["P1_URGENT", "P2_STANDARD", "P3_LOW"],
                default=["P1_URGENT", "P2_STANDARD", "P3_LOW"]
            )
        with col_f2:
            dostupne_kat = sorted(list({z["kategorie"] for z in historie}))
            filtr_kategorie = st.multiselect(
                "Filtr kategorie:",
                options=dostupne_kat,
                default=dostupne_kat
            )

        filtrovana_data = [
            z for z in historie
            if z["priorita"] in filtr_priorita and z["kategorie"] in filtr_kategorie
        ]

        st.caption(f"Zobrazeno zpráv: {len(filtrovana_data)}")
        
        if filtrovana_data:
            tabulka = []
            for z in filtrovana_data:
                ikona_prio = "🔴 P1 Urgent" if z["priorita"] == "P1_URGENT" else ("🟡 P2 Běžná" if z["priorita"] == "P2_STANDARD" else "⚪ P3 Info")
                tabulka.append({
                    "Priorita": ikona_prio,
                    "Kategorie": z["kategorie"],
                    "Odesílatel": z["odesilatel"].split("<")[0].strip().strip('"'),
                    "Předmět": z["predmet"],
                    "AI Shrnutí agendy": z["shrnuti"],
                    "Příloha": f"📎 {z['prilohy']}" if z.get("prilohy") else "—",
                    "Odkaz": z["gmail_url"]
                })

            st.dataframe(
                tabulka,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Odkaz": st.column_config.LinkColumn("Akce", display_text="Otevřít v Gmailu ↗"),
                    "AI Shrnutí agendy": st.column_config.TextColumn(width="large"),
                }
            )
        else:
            st.warning("Žádné zprávy neodpovídají zvolenému filtru.")

with tab_nastaveni:
    st.subheader("Firemní pravidla, štítky a barvy v Gmailu")
    st.caption("Změny barev se po uložení automaticky propíší přímo do vašeho účtu Gmail.")
    
    konfig = nacti_config()
    
    with st.container(border=True):
        col_firm1, col_firm2 = st.columns(2, gap="large")
        with col_firm1:
            novy_popis_firmy = st.text_input("Obor podnikání / kontext firmy:", value=konfig.get("firma_popis", ""))
            st.caption("Slouží jako kontext pro AI při vyhodnocování naléhavosti e-mailů.")
        with col_firm2:
            vip_text = st.text_area(
                "VIP odesílatelé nebo domény (jeden na řádek — vždy priorita P1):",
                value="\n".join(konfig.get("vip_odesilatele", [])),
                height=90
            )

    st.write("")
    st.markdown("#### Nastavení štítků a jejich barev")
    
    h1, h2, h3, h4 = st.columns([1.8, 3.2, 0.9, 1.0])
    h1.markdown('<div class="table-header">Štítek v Gmailu</div>', unsafe_allow_html=True)
    h2.markdown('<div class="table-header">Pravidlo pro AI zařazení</div>', unsafe_allow_html=True)
    h3.markdown('<div class="table-header">Barva</div>', unsafe_allow_html=True)
    h4.markdown('<div class="table-header">Archivace</div>', unsafe_allow_html=True)

    upraveno_kategorie = {}
    
    for nazev, info in konfig.get("kategorie", {}).items():
        with st.container(border=True):
            c_nazev, c_popis, c_barva, c_arch = st.columns([1.8, 3.2, 0.9, 1.0], vertical_alignment="center")
            
            with c_barva:
                vybrana_barva = vykresli_vyber_barvy(nazev, info.get("barva", "Šedá"))
            
            barva_hex = GMAIL_BARVY.get(vybrana_barva, GMAIL_BARVY["Šedá"])
            with c_nazev:
                st.markdown(
                    f'<span class="label-preview" style="background-color:{barva_hex["backgroundColor"]}; color:{barva_hex["textColor"]};">AI/{nazev}</span>',
                    unsafe_allow_html=True
                )
            with c_popis:
                novy_popis = st.text_input("Pravidlo", value=info["popis"], key=f"popis_{nazev}", label_visibility="collapsed")
            with c_arch:
                nova_arch = st.checkbox("Uklidit", value=info.get("archivovat", False), key=f"arch_{nazev}")
                
            upraveno_kategorie[nazev] = {
                "popis": novy_popis,
                "archivovat": nova_arch,
                "barva": vybrana_barva
            }

    st.write("")
    st.markdown("#### Přidat nový štítek")
    with st.container(border=True):
        c_new1, c_new2, c_new3, c_new4 = st.columns([1.8, 3.2, 0.9, 1.0], vertical_alignment="center")
        novy_nazev_kat = c_new1.text_input("Název", placeholder="Např. Objednavky", label_visibility="collapsed")
        novy_popis_kat = c_new2.text_input("Popis", placeholder="Jaké e-maily sem zařadit...", label_visibility="collapsed")
        with c_new3:
            nova_barva_kat = vykresli_vyber_barvy("novy_stitek", "Zelená")
        with c_new4:
            novy_arch_kat = st.checkbox("Uklidit", key="new_arch")

    st.write("")
    if st.button("Uložit nastavení a propisovat barvy do Gmailu", type="primary"):
        konfig["firma_popis"] = novy_popis_firmy
        konfig["vip_odesilatele"] = [r.strip() for r in vip_text.splitlines() if r.strip()]
        konfig["kategorie"] = upraveno_kategorie
        
        if novy_nazev_kat.strip() and novy_popis_kat.strip():
            cisty_klic = novy_nazev_kat.strip().replace(" ", "_")
            konfig["kategorie"][cisty_klic] = {
                "popis": novy_popis_kat.strip(),
                "archivovat": novy_arch_kat,
                "barva": nova_barva_kat
            }
            
        uloz_config(konfig)
        with st.spinner("Synchronizuji štítky a barvy přímo do Gmailu..."):
            synchronizuj_barvy_stitku()
        st.toast("Nastavení uloženo a barvy v Gmailu aktualizovány!", icon="✅")
        st.rerun()

with tab_log:
    st.subheader("Záznam systémových operací")
    if os.path.exists("bot.log"):
        with open("bot.log", "r", encoding="utf-8") as f:
            radky = f.readlines()[-20:]
        st.code("".join(radky), language="text")
    else:
        st.info("Zatím neexistuje žádný log.")