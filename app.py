import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json, os, io
import streamlit_authenticator as stauth
import bcrypt

from scraper_brvm import get_all_data, TICKERS_BRVM
from signals import build_dataframe, add_indicators, generate_signal, get_top5
from alerts import check_and_send_alerts, generate_pdf_report

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BRVM Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS GLOBAL ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background-color: #080B12; color: #E2D9C5; }
  .metric-card {
    background: #0D1117; border: 1px solid #1C2333;
    border-radius: 8px; padding: 12px 16px; margin: 4px;
  }
  .signal-badge {
    display: inline-block; padding: 4px 12px;
    border-radius: 4px; font-weight: bold; font-size: 0.85rem;
  }
  div[data-testid="stSidebar"] { background-color: #0D1117; }
  .top5-card {
    background: #0D1117; border: 1px solid #1C2333;
    border-radius: 8px; padding: 10px 14px; margin: 6px 0;
    cursor: pointer; transition: border-color 0.2s;
  }
  .top5-card:hover { border-color: #D4A843; }
</style>
""", unsafe_allow_html=True)

# ── AUTHENTIFICATION ─────────────────────────────────────────────────────────
def check_login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px'>
            <h1 style='color:#D4A843;font-size:2.5rem'>🏛️ BRVM Analytics</h1>
            <p style='color:#6B7280'>Plateforme d'analyse professionnelle</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            with st.form("login_form"):
                st.markdown("### 🔐 Connexion")
                username = st.text_input("Identifiant")
                password = st.text_input("Mot de passe", type="password")
                submitted = st.form_submit_button("Se connecter", use_container_width=True)
                
                if submitted:
                    ADMIN_USER = st.secrets.get("auth", {}).get("username", "admin")
                    ADMIN_PASS = st.secrets.get("auth", {}).get("password", "brvm2024")
                    if username == ADMIN_USER and password == ADMIN_PASS:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("❌ Identifiants incorrects")
        st.stop()

check_login()

# ── CHARGEMENT DONNÉES ───────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Chargement des données BRVM...")
def load_data(force=False):
    return get_all_data(force_refresh=force)

@st.cache_data(ttl=3600, show_spinner="Calcul des signaux...")
def compute_all_signals(data_hash):
    data = load_data()
    signals = {}
    for company in TICKERS_BRVM:
        t = company["ticker"]
        co_data = data.get(t, {})
        hist    = co_data.get("historique", [])
        df      = build_dataframe(hist)
        df      = add_indicators(df) if df is not None else None
        sig     = generate_signal(df, co_data)
        sig["name"]    = company["name"]
        sig["sector"]  = company["sector"]
        sig["country"] = company["country"]
        sig["flag"]    = company["flag"]
        sig["df"]      = df
        signals[t]     = sig
    return signals

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:10px'>
        <h2 style='color:#D4A843;margin:0'>🏛️ BRVM</h2>
        <p style='color:#6B7280;font-size:0.7rem;margin:0'>Analytics Platform</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    page = st.radio("📍 Navigation", [
        "🏠 Tableau de bord",
        "📊 Analyse détaillée",
        "📈 Graphique avancé",
        "🔮 Projections",
        "⚖️ Comparaison",
        "⚙️ Paramètres"
    ])
    
    st.divider()
    
    # Forcer refresh
    if st.button("🔄 Actualiser données", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Dernière MAJ
    st.markdown(f"<div style='color:#6B7280;font-size:0.65rem;text-align:center'>MAJ: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>", unsafe_allow_html=True)
    
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── CHARGEMENT ───────────────────────────────────────────────────────────────
with st.spinner("Chargement..."):
    all_data    = load_data()
    all_signals = compute_all_signals(str(datetime.now().date()))

top_buy, top_sell = get_top5(all_signals)
news = all_data.get("_news", [])

# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — TABLEAU DE BORD
# ════════════════════════════════════════════════════════════════════════════
if "Tableau" in page:
    st.markdown("## 🏠 Tableau de bord — Marché BRVM")
    
    # ── KPIs marché
    scores = [v["score"] for v in all_signals.values()]
    nb_buy  = sum(1 for s in scores if s >= 65)
    nb_sell = sum(1 for s in scores if s < 35)
    avg_sc  = np.mean(scores)
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📊 Actions cotées", len(TICKERS_BRVM))
    k2.metric("🟢 Signaux ACHAT", nb_buy)
    k3.metric("🔴 Signaux VENTE", nb_sell)
    k4.metric("📈 Score moyen", f"{avg_sc:.0f}/100")
    k5.metric("🕐 Dernière MAJ", datetime.now().strftime("%H:%M"))
    
    st.divider()
    
    col_buy, col_sell = st.columns(2)
    
    with col_buy:
        st.markdown("### 🟢 TOP 5 — À ACHETER")
        for ticker, sig in top_buy:
            with st.container():
                if st.button(
                    f"{sig['flag'] if 'flag' in sig else ''} **{ticker}** — {sig['name']}\n"
                    f"Score: **{sig['score']}/100** | {sig['signal']} | RSI: {sig['last_rsi']:.1f}",
                    key=f"buy_{ticker}",
                    use_container_width=True
                ):
                    st.session_state["selected_ticker"] = ticker
                    st.session_state["goto_detail"] = True
    
    with col_sell:
        st.markdown("### 🔴 TOP 5 — À VENDRE")
        for ticker, sig in top_sell:
            with st.container():
                if st.button(
                    f"{sig.get('flag','')} **{ticker}** — {sig['name']}\n"
                    f"Score: **{sig['score']}/100** | {sig['signal']} | RSI: {sig['last_rsi']:.1f}",
                    key=f"sell_{ticker}",
                    use_container_width=True
                ):
                    st.session_state["selected_ticker"] = ticker
                    st.session_state["goto_detail"] = True
    
    st.divider()
    
    # ── Tableau complet marché
    st.markdown("### 📋 Vue d'ensemble — Toutes les actions")
    
    sector_filter = st.selectbox("Filtrer par secteur", 
        ["Tous"] + sorted(list(set(s["sector"] for s in all_signals.values()))))
    
    rows = []
    for ticker, sig in sorted(all_signals.items(), key=lambda x: x[1]["score"], reverse=True):
        if sector_filter != "Tous" and sig.get("sector") != sector_filter:
            continue
        rows.append({
            "": sig.get("flag",""),
            "Ticker": ticker,
            "Société": sig.get("name",""),
            "Pays": sig.get("country",""),
            "Secteur": sig.get("sector",""),
            "Signal": sig["signal"],
            "Score": sig["score"],
            "Cours": f"{sig['last_close']:,.0f}",
            "RSI": f"{sig['last_rsi']:.1f}",
        })
    
    df_display = pd.DataFrame(rows)
    
    def color_signal(val):
        colors = {
            "ACHAT FORT": "background-color:#16532d;color:white",
            "ACHAT": "background-color:#1a4d1a;color:white",
            "CONSERVER": "background-color:#4d3d00;color:white",
            "ALLÉGER": "background-color:#4d1f00;color:white",
            "VENDRE": "background-color:#4d0000;color:white",
        }
        return colors.get(val, "")
    
    styled = df_display.style.applymap(color_signal, subset=["Signal"])
    st.dataframe(styled, use_container_width=True, hide_index=True, height=400)
    
    # ── Actualités
    st.divider()
    st.markdown("### 📰 Actualités BRVM")
    if news:
        for item in news[:6]:
            st.markdown(f"• [{item['title']}]({item['link']}) — *{item.get('source','')}*")
    else:
        st.info("Aucune actualité disponible")

# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ANALYSE DÉTAILLÉE
# ════════════════════════════════════════════════════════════════════════════
elif "Analyse" in page:
    st.markdown("## 📊 Analyse détaillée")
    
    default_t = st.session_state.get("selected_ticker", "SNTS")
    ticker = st.selectbox("Choisir une action", 
        [c["ticker"] for c in TICKERS_BRVM],
        index=[c["ticker"] for c in TICKERS_BRVM].index(default_t) if default_t in [c["ticker"] for c in TICKERS_BRVM] else 0
    )
    
    sig  = all_signals.get(ticker, {})
    df   = sig.get("df")
    co   = all_data.get(ticker, {})
    fond = co.get("fondamentaux", {})
    
    # ── Header société
    col_h1, col_h2, col_h3 = st.columns([2,1,1])
    with col_h1:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size:1.5rem;font-weight:700'>{sig.get('flag','')} {sig.get('name','')}</div>
            <div style='color:#6B7280'>{sig.get('country','')} · {sig.get('sector','')}</div>
            <div style='font-size:1.8rem;font-weight:700;color:#D4A843'>{sig['last_close']:,.0f} FCFA</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_h2:
        score = sig["score"]
        color = sig["color"]
        st.markdown(f"""
        <div class='metric-card' style='text-align:center'>
            <div style='font-size:2.5rem;font-weight:900;color:{color}'>{score}</div>
            <div style='font-size:0.7rem;color:#6B7280'>SCORE /100</div>
            <div style='background:{color};color:white;padding:4px 10px;border-radius:4px;font-weight:700;margin-top:8px'>{sig['signal']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_h3:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size:0.65rem;color:#6B7280'>RSI (14)</div>
            <div style='font-size:1.4rem;font-weight:700'>{sig['last_rsi']:.1f}</div>
            <div style='font-size:0.65rem;color:#6B7280;margin-top:6px'>MACD</div>
            <div style='font-size:1.1rem;color:{"#22C55E" if sig["last_macd"]>0 else "#EF4444"}'>{sig['last_macd']:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # ── Résumé analyse
    st.markdown("### 🔍 Résumé d'analyse")
    st.markdown(sig.get("resume","Données insuffisantes"))
    
    with st.expander("📋 Tous les points d'analyse"):
        for p in sig.get("points", []):
            st.write(p)
    
    # ── Fondamentaux
    st.divider()
    st.markdown("### 📑 Analyse Fondamentale")
    
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("PER", fond.get("per", co.get("per", "N/D")))
    f2.metric("Capitalisation", fond.get("mktcap", co.get("mktcap", "N/D")))
    f3.metric("Dividende", fond.get("dividende", "N/D"))
    f4.metric("Rend. dividende", 
        f"{(fond.get('dividende',0)/sig['last_close']*100):.2f}%" if sig['last_close'] > 0 and fond.get('dividende') else "N/D")
    
    # Historique dividendes
    hist_prices = co.get("historique", [])
    if hist_prices:
        df_hist = build_dataframe(hist_prices)
        if df_hist is not None and len(df_hist) > 0:
            st.markdown("#### 📅 Historique des cours")
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Scatter(
                x=df_hist["date"], y=df_hist["close"],
                mode="lines", name="Cours clôture",
                line=dict(color="#D4A843", width=2)
            ))
            fig_hist.update_layout(
                template="plotly_dark", paper_bgcolor="#0D1117",
                plot_bgcolor="#0D1117", height=300,
                margin=dict(l=10,r=10,t=10,b=10)
            )
            st.plotly_chart(fig_hist, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 — GRAPHIQUE AVANCÉ
# ════════════════════════════════════════════════════════════════════════════
elif "Graphique" in page:
    st.markdown("## 📈 Graphique Technique Avancé")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        ticker = st.selectbox("Action", [c["ticker"] for c in TICKERS_BRVM],
            index=0, key="chart_ticker")
    with col_s2:
        periode = st.selectbox("Période", ["1 mois","3 mois","6 mois","1 an","2 ans","5 ans","Max"], index=3)
    with col_s3:
        freq = st.selectbox("Fréquence", ["Journalier","Hebdomadaire","Mensuel"], index=0)
    with col_s4:
        chart_type = st.selectbox("Type graphe", ["Bougies","Ligne","Aire"], index=0)
    
    # Indicateurs à afficher
    st.markdown("**Indicateurs techniques :**")
    ic1, ic2, ic3, ic4, ic5, ic6 = st.columns(6)
    show_ma   = ic1.checkbox("MA20/50/200", value=True)
    show_bb   = ic2.checkbox("Bollinger", value=True)
    show_rsi  = ic3.checkbox("RSI", value=True)
    show_macd = ic4.checkbox("MACD", value=True)
    show_vol  = ic5.checkbox("Volume", value=True)
    show_stoch= ic6.checkbox("Stochastique", value=False)
    
    sig = all_signals.get(ticker, {})
    df  = sig.get("df")
    
    if df is None or len(df) < 5:
        st.warning("⚠️ Données insuffisantes pour ce ticker")
        st.stop()
    
    # Filtrer par période
    period_map = {
        "1 mois": 30, "3 mois": 90, "6 mois": 180,
        "1 an": 365, "2 ans": 730, "5 ans": 1825, "Max": 99999
    }
    days = period_map[periode]
    cutoff = datetime.now() - timedelta(days=days)
    df_plot = df[df["date"] >= pd.Timestamp(cutoff)].copy()
    
    # Rééchantillonnage
    if freq == "Hebdomadaire":
        df_plot = df_plot.set_index("date").resample("W").agg({
            "open":"first","high":"max","low":"min","close":"last","volume":"sum"
        }).dropna().reset_index()
    elif freq == "Mensuel":
        df_plot = df_plot.set_index("date").resample("M").agg({
            "open":"first","high":"max","low":"min","close":"last","volume":"sum"
        }).dropna().reset_index()
    
    # Recalculer indicateurs sur df_plot
    df_plot = add_indicators(df_plot)
    
    # ── Nombre de sous-graphiques
    n_rows = 1
    row_heights = [0.5]
    specs_list  = [{"secondary_y": False}]
    
    if show_vol:
        n_rows += 1; row_heights.append(0.1); specs_list.append({"secondary_y": False})
    if
