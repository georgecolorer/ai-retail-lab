import os
import truststore
truststore.inject_into_ssl()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from gmail_connect import pripoj_gmail
from triage_bot import spust_trideni

st.set_page_config(page_title="Gmail AI Triage Dashboard", page_icon="📬", layout="wide")

st.title("📬 Gmail AI Triage – Manažerský přehled")
st.markdown("Automatické paralelní třídění a prioritizace příchozí pošty pomocí **Google Gemini AI**.")

with st.sidebar:
    st.header("⚡ Běžný provoz")
    pocet_mailu = st.slider("Počet nových e-mailů", min_value=5, max_value=30, value=15)
    jen_neprectene = st.checkbox("Třídit pouze nepřečtené zprávy", value=False)
    
    if st.button("🚀 Spustit třídění Inboxu", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def aktualizuj_stav(hotovo, celkem, predmet):
            progress_bar.progress(hotovo / celkem)
            status_text.caption(f"Zpracováno {hotovo}/{celkem}: {predmet[:35]}...")

        pocet = spust_trideni(
            pocet_zprav=pocet_mailu,
            jen_neprectene=jen_neprectene,
            progress_callback=aktualizuj_stav
        )
        st.cache_data.clear()
        st.success(f"Hotovo! Zpracováno {pocet} e-mailů.")
        st.rerun()

    st.divider()
    st.header("🧹 Počáteční úklid (Nový účet)")
    st.caption("Hromadné roztřídění starší pošty při prvním nasazení.")
    pocet_uklid = st.selectbox("Velikost dávky pro úklid", options=[50, 100, 200], index=0)
    
    if st.button("🧹 Spustit hromadný úklid", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def aktualizuj_uklid(hotovo, celkem, predmet):
            progress_bar.progress(hotovo / celkem)
            status_text.caption(f"Úklid {hotovo}/{celkem}: {predmet[:35]}...")

        pocet = spust_trideni(
            pocet_zprav=pocet_uklid,
            jen_neprectene=False,
            progress_callback=aktualizuj_uklid
        )
        st.cache_data.clear()
        st.success(f"Úklid dokončen! Roztříděno {pocet} starších zpráv.")
        st.rerun()

@st.cache_data(ttl=30)
def nacti_statistiky_gmailu():
    service = pripoj_gmail()
    odpoved_stitky = service.users().labels().list(userId="me").execute()
    ai_stitky = [s for s in odpoved_stitky.get("labels", []) if s["name"].startswith("AI/") and s["name"] != "AI/Zpracovano"]
    
    statistiky = {}
    for stitek in ai_stitky:
        detail = service.users().labels().get(userId="me", id=stitek["id"]).execute()
        cisty_nazev = stitek["name"].replace("AI/", "")
        statistiky[cisty_nazev] = detail.get("messagesTotal", 0)
    return statistiky

try:
    data = nacti_statistiky_gmailu()
    
    col1, col2, col3 = st.columns(3)
    urgentni = data.get("P1-URGENT", 0)
    celkem_ai = sum(v for k, v in data.items() if k != "P1-URGENT")
    
    col1.metric("🚨 Urgentní k řešení (P1)", urgentni)
    col2.metric("📂 Celkem roztříděno AI", celkem_ai)
    col3.metric("🏷️ Aktivních kategorií", len([k for k in data.keys() if k != "P1-URGENT"]))

    st.divider()

    levy_sloupec, pravy_sloupec = st.columns([1, 1])

    with levy_sloupec:
        st.subheader("📊 Rozložení e-mailů podle kategorií")
        kategorie_data = {k: v for k, v in data.items() if k != "P1-URGENT"}
        if kategorie_data:
            st.bar_chart(kategorie_data)
        else:
            st.info("Zatím nejsou k dispozici žádná data. Spusť třídění v levém panelu.")

    with pravy_sloupec:
        st.subheader("📜 Poslední záznamy z běhu bota")
        if os.path.exists("bot.log"):
            with open("bot.log", "r", encoding="utf-8") as f:
                radky = f.readlines()[-12:]
            st.code("".join(radky), language="text")
        else:
            st.info("Soubor bot.log zatím neexistuje.")

except Exception as e:
    st.error(f"Nepodařilo se načíst data z Gmailu: {e}")
