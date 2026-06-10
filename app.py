# app.py — Version enrichie BRVM Dashboard
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from analyse import (COMPANIES, YEARS, calc_metrics,
                     project_prices, get_market_kpis)

st.set_page_config(
    page_title="BRVM Dashboard", page_icon="📈",
    layout="wide", initial_sidebar_state="expanded"
)

# ── CSS DARK THEME ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #080B12; color: #E2D9C5; }
    .metric-card {
        background: #0D1117; border: 1px solid #1C2333;
        border-radius: 8px; padding: 12px 16px; margin: 4px;
    }
    .signal-badge {
        padding: 4px 12px; border-radius: 4px;
        font-weight: 700; font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("## 📈 BRVM Dashboard — Analyse 10 ans")
st.caption("Bourse Régionale des Valeurs Mobilières — Sources: BRVM BOC · Sikafinance · Rapports annuels")

# ── KPIs MARCHÉ ───────────────────────────────────────────────────────────────
kpis = get_market_kpis()
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("🏢 Sociétés cotées", kpis["nb_societes"])
k2.metric("💰 Capitalisation", f"{kpis['total_cap']:,} Mds FCFA")
k3.metric("📊 Rend. moyen", f"{kpis['avg_yield']}%")
k4.metric("📈 Perf. moy. 5 ans", f"+{kpis['avg_perf5']}%")
k5.metric("✅ Signaux ACHAT", kpis["buy_signals"])

st.divider()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filtres")
    sectors = ["Tous"] + list(set(c["sector"] for c in COMPANIES))
    sector_filter = st.selectbox("Secteur", sectors)
    sort_by = st.selectbox("Trier par", ["Score","Perf. 5 ans","Rendement div."])
    st.divider()
    st.markdown("### 📌 Sélectionner une action")

    filtered = [c for c in COMPANIES
                if sector_filter == "Tous" or c["sector"] == sector_filter]

    def sort_key(c):
        m = calc_metrics(c)
        if sort_by == "Score": return m["score"] if m else 0
        if sort_by == "Perf. 5 ans": return m["perf5"] or 0 if m else 0
        return m["yield_"] if m else 0

    filtered = sorted(filtered, key=sort_key, reverse=True)

    selected_ticker = st.radio(
        "Action",
        [c["ticker"] for c in filtered],
        format_func=lambda t: next(
            f"{c['flag']} {c['ticker']} — {c['name']}"
            for c in COMPANIES if c["ticker"] == t
        )
    )

# ── COMPAGNIE SÉLECTIONNÉE ────────────────────────────────────────────────────
company = next(c for c in COMPANIES if c["ticker"] == selected_ticker)
metrics = calc_metrics(company)

# ── ONGLETS ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Vue d'ensemble",
    "📈 Graphiques",
    "🔮 Projections",
    "⚖️ Comparaison"
])

# ══ TAB 1 : VUE D'ENSEMBLE ════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(f"### {company['flag']} {company['name']} ({company['ticker']})")
        st.caption(f"{company['sector']} · {company['country']}")

        score = metrics["score"]
        signal = metrics["signal"]
        color_map = {
            "ACHAT FORT":"#22C55E","ACHAT":"#84CC16",
            "CONSERVER":"#D4A843","ALLÉGER":"#F97316","VENDRE":"#EF4444"
        }
        c = color_map.get(signal, "#94A3B8")
        st.markdown(f"""
        <div style='background:{c}22;border:2px solid {c};border-radius:8px;
                    padding:16px;text-align:center;margin:10px 0'>
            <div style='font-size:1.8rem;font-weight:900;color:{c}'>{signal}</div>
            <div style='color:#E2D9C5;font-size:1.1rem'>Score: {score}/100</div>
        </div>
        """, unsafe_allow_html=True)

        st.metric("💵 Cours actuel", f"{metrics['current_price']:,} FCFA")
        st.metric("💸 Dividende", f"{metrics['current_div']:,} FCFA/action")
        st.metric("📊 Rendement div.", f"{metrics['yield_']}%")
        st.metric("📈 Perf. 5 ans", f"+{metrics['perf5']}%" if metrics["perf5"] else "N/D")
        st.metric("📉 Volatilité", f"{metrics['volat']}%")
        st.metric("⚠️ Risque", metrics["risk"])
        st.metric("💹 PER", company["per"])
        st.metric("🏦 Cap. boursière", f"{company['mktcap']} Mds FCFA")

    with col2:
        # Tableau historique
        st.markdown("#### 📋 Historique 2015 → 2026")
        rows = []
        prev_price = None
        for y in YEARS:
            p = company["prices"][y]
            d = company["dividends"].get(y, 0)
            if p > 0:
                perf = round((p/prev_price-1)*100, 1) if prev_price else None
                rend = round(d/p*100, 2) if d > 0 else None
                rows.append({
                    "Année": y,
                    "Cours (FCFA)": f"{p:,}",
                    "Dividende": f"{d:,}" if d > 0 else "—",
                    "Perf. annuelle": f"+{perf}%" if perf and perf >= 0 else f"{perf}%" if perf else "—",
                    "Rend. div.": f"{rend}%" if rend else "—"
                })
                prev_price = p
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══ TAB 2 : GRAPHIQUES ════════════════════════════════════════════════════════
with tab2:
    valid_data = [(y, company["prices"][y], company["dividends"].get(y,0))
                  for y in YEARS if company["prices"][y] > 0]
    years_v = [d[0] for d in valid_data]
    prices_v = [d[1] for d in valid_data]
    divs_v = [d[2] for d in valid_data]

    # Graphique cours
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=years_v, y=prices_v, mode="lines+markers",
        name="Cours (FCFA)", line=dict(color="#D4A843", width=2.5),
        fill="tozeroy", fillcolor="rgba(212,168,67,0.1)"
    ))
    fig1.update_layout(
        title=f"Évolution du cours — {company['name']}",
        template="plotly_dark", paper_bgcolor="#0D1117",
        plot_bgcolor="#0D1117", height=350
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Graphique dividendes
    div_data = [(y,d) for y,d in zip(years_v, divs_v) if d > 0]
    if div_data:
        fig2 = go.Figure(go.Bar(
            x=[d[0] for d in div_data], y=[d[1] for d in div_data],
            name="Dividende", marker_color="#14B8A6"
        ))
        fig2.update_layout(
            title="Dividendes distribués (FCFA/action)",
            template="plotly_dark", paper_bgcolor="#0D1117",
            plot_bgcolor="#0D1117", height=300
        )
        st.plotly_chart(fig2, use_container_width=True)

# ══ TAB 3 : PROJECTIONS ═══════════════════════════════════════════════════════
with tab3:
    st.markdown(f"#### 🔮 Projection — {company['name']}")
    st.caption("Régression linéaire sur données historiques · Scénarios ±15%")

    proj_years = st.select_slider("Horizon de projection", [3,5,7,10], value=5)
    projections = project_prices(company, proj_years)

    if projections:
        fig3 = go.Figure()
        # Historique
        fig3.add_trace(go.Scatter(
            x=years_v, y=prices_v, name="Historique",
            line=dict(color="#D4A843", width=2)
        ))
        proj_x = [p["year"] for p in projections]
        fig3.add_trace(go.Scatter(
            x=proj_x, y=[p["optimiste"] for p in projections],
            name="Optimiste +15%", line=dict(color="#22C55E", dash="dot")
        ))
        fig3.add_trace(go.Scatter(
            x=proj_x, y=[p["central"] for p in projections],
            name="Central", line=dict(color="#94A3B8", dash="dash")
        ))
        fig3.add_trace(go.Scatter(
            x=proj_x, y=[p["pessimiste"] for p in projections],
            name="Pessimiste -15%", line=dict(color="#EF4444", dash="dot")
        ))
        fig3.update_layout(
            template="plotly_dark", paper_bgcolor="#0D1117",
            plot_bgcolor="#0D1117", height=400
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Tableau projections
        current = metrics["current_price"]
        proj_rows = []
        for p in projections:
            pot = round((p["central"]/current-1)*100, 1) if current else 0
            proj_rows.append({
                "Année": p["year"],
                "Cours central": f"{p['central']:,}",
                "Optimiste": f"{p['optimiste']:,}",
                "Pessimiste": f"{p['pessimiste']:,}",
                "Potentiel": f"+{pot}%" if pot >= 0 else f"{pot}%"
            })
        st.dataframe(pd.DataFrame(proj_rows), use_container_width=True, hide_index=True)

    st.warning("⚠️ Projections basées sur la régression linéaire. Non garanties. À titre informatif uniquement.")

# ══ TAB 4 : COMPARAISON ═══════════════════════════════════════════════════════
with tab4:
    st.markdown("#### ⚖️ Comparaison multi-actions")
    tickers_all = [c["ticker"] for c in COMPANIES]
    selected_comp = st.multiselect(
        "Sélectionnez jusqu'à 5 actions",
        tickers_all,
        default=tickers_all[:3],
        max_selections=5
    )

    if selected_comp:
        # Performance relative base 100
        fig4 = go.Figure()
        for t in selected_comp:
            co = next(c for c in COMPANIES if c["ticker"] == t)
            valid = [(y, co["prices"][y]) for y in YEARS if co["prices"][y] > 0]
            if len(valid) >= 2:
                base = valid[0][1]
                fig4.add_trace(go.Scatter(
                    x=[v[0] for v in valid],
                    y=[round(v[1]/base*100) for v in valid],
                    name=t, mode="lines+markers"
                ))
        fig4.update_layout(
            title="Performance relative (base 100)",
            template="plotly_dark", paper_bgcolor="#0D1117",
            plot_bgcolor="#0D1117", height=400
        )
        st.plotly_chart(fig4, use_container_width=True)

        # Tableau comparatif
        comp_rows = []
        for t in selected_comp:
            co = next(c for c in COMPANIES if c["ticker"] == t)
            m = calc_metrics(co)
            if m:
                comp_rows.append({
                    "Ticker": t,
                    "Société": co["name"],
                    "Score": m["score"],
                    "Signal": m["signal"],
                    "Perf. 5 ans": f"+{m['perf5']}%" if m["perf5"] else "N/D",
                    "Rend. div.": f"{m['yield_']}%",
                    "Risque": m["risk"],
                    "PER": co["per"],
                })
        st.dataframe(
            pd.DataFrame(comp_rows).sort_values("Score", ascending=False),
            use_container_width=True, hide_index=True
        )

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Sources : BRVM BOC · Sikafinance · RichBourse · Rapports annuels · ⚠️ Analyse informative uniquement.")
