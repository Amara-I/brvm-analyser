"""
app.py - Application Streamlit BRVM
===================================
Dashboard complet pour l'analyse des actions BRVM.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Import des modules locaux
import signals
import alerts

# ============================================================================
# CONFIGURATION STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="BRVM Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': '📊 BRVM Analytics - Analyse Technique & Fondamentale',
        'Get Help': None,
        'Report a bug': None
    }
)

# Configuration du style
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .sidebar .stButton > button {
        width: 100%;
        margin-bottom: 10px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
    .recommendation-achat {
        background-color: #d5f4e6;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #27ae60;
    }
    .recommendation-vente {
        background-color: #fadbd8;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #e74c3c;
    }
    .recommendation-conserver {
        background-color: #fdebd0;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #f39c12;
    }
    </style>
""", unsafe_allow_html=True)


# ============================================================================
# GESTION DE L'AUTHENTIFICATION
# ============================================================================

def check_authentication():
    """
    Vérifie l'authentification de l'utilisateur.
    Charge les logins depuis st.secrets ou utilise admin/admin par défaut.
    """
    # Essayer de charger depuis secrets.toml
    try:
        admin_users = dict(st.secrets.get("auth", {}).get("admin", {}))
        read_only_users = dict(st.secrets.get("auth", {}).get("users", {}))
    except:
        # Fallback: utiliser les crédentials par défaut pour les tests
        admin_users = {"admin": "admin123", "admin@example.com": "password"}
        read_only_users = {"user": "user123", "user@example.com": "password"}
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.is_admin = False
    
    if not st.session_state.authenticated:
        # Page de login
        st.markdown("""
            <div style="text-align: center; padding: 50px;">
                <h1>🔐 Connexion BRVM Analytics</h1>
                <p>Veuillez entrer vos identifiants pour accéder à l'application.</p>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                username = st.text_input("👤 Nom d'utilisateur")
                password = st.text_input("🔑 Mot de passe", type="password")
                submit = st.form_submit_button("Se connecter", type="primary")
                
                if submit:
                    # Vérifier admin
                    if username in admin_users and admin_users[username] == password:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.is_admin = True
                        st.rerun()
                    # Vérifier users
                    elif username in read_only_users and read_only_users[username] == password:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.is_admin = False
                        st.rerun()
                    else:
                        st.error("❌ Identifiants incorrects")
        
        # Info pour les tests
        st.info("💡 Pour les tests: admin/admin123 ou user/user123")
        return False
    
    return True


def logout():
    """Déconnexion."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.is_admin = False
    st.rerun()


# ============================================================================
# FONCTIONS D'AFFICHAGE
# ============================================================================

def format_number(number: float, decimals: int = 2) -> str:
    """Formate un nombre avec les séparateurs appropriés."""
    if number is None:
        return "N/A"
    return f"{number:,.{decimals}f}".replace(",", " ")


def get_recommendation_style(recommendation: str) -> str:
    """Retourne le style CSS pour la recommandation."""
    styles = {
        "ACHAT": "recommendation-achat",
        "VENTE": "recommendation-vente",
        "CONSERVER": "recommendation-conserver",
        "NEUTRE": "recommendation-conserver"
    }
    return styles.get(recommendation, "")


def plot_candlestick(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    Crée un graphique chandelier pour les données historiques.
    """
    if df is None or len(df) == 0:
        return None
    
    fig = go.Figure(data=[go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=ticker
    )])
    
    fig.update_layout(
        title=f"Cours {ticker}",
        yaxis_title="Prix (XOF)",
        xaxis_title="Date",
        template="plotly_white",
        height=400,
        xaxis_rangeslider_visible=False
    )
    
    return fig


def plot_indicators(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    Crée un graphique multi-indicateurs (RSI, MACD, Prix + SMA).
    """
    if df is None or len(df) < 20:
        return None
    
    # Calculer les indicateurs
    close = df['close']
    rsi = signals.calculate_rsi(close, 14)
    macd_line, signal_line = signals.calculate_macd(close)
    sma_20 = signals.calculate_sma(close, 20)
    sma_50 = signals.calculate_sma(close, 50)
    
    # Créer figure avec sous-graphes
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Prix + SMA", "MACD", "RSI")
    )
    
    # Prix + SMA
    fig.add_trace(go.Scatter(x=df['date'], y=df['close'], 
                             name="Prix", line=dict(color='black', width=2)), 
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=sma_20, 
                             name="SMA 20", line=dict(color='blue', width=1)), 
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=sma_50, 
                             name="SMA 50", line=dict(color='red', width=1)), 
                  row=1, col=1)
    
    # MACD
    fig.add_trace(go.Scatter(x=df['date'], y=macd_line, 
                             name="MACD", line=dict(color='blue')), 
                  row=2, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=signal_line, 
                             name="Signal", line=dict(color='orange')), 
                  row=2, col=1)
    fig.add_trace(go.Bar(x=df['date'], y=macd_line - signal_line, 
                         name="Histogramme", marker_color='gray'), 
                  row=2, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df['date'], y=rsi, 
                             name="RSI", line=dict(color='purple')), 
                  row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    fig.update_layout(
        height=600,
        template="plotly_white",
        showlegend=True
    )
    
    return fig


def plot_projection(df: pd.DataFrame, days: int = 30) -> go.Figure:
    """
    Crée une projection simple basée sur la tendance linéaire.
    """
    if df is None or len(df) < 10:
        return None
    
    # Projection linéaire simple (à des fins d'illustration)
    close = df['close'].values
    x = np.arange(len(close))
    
    # Régression linéaire
    coeffs = np.polyfit(x, close, 1)
    trend = np.poly1d(coeffs)
    
    # Générer les dates futures
    last_date = df['date'].iloc[-1]
    future_dates = pd.date_range(start=last_date, periods=days + 1, freq='D')[1:]
    
    # Calculer les valeurs futures
    future_x = np.arange(len(close), len(close) + days)
    projected_values = trend(future_x)
    
    # Ajouter un peu de volatilité simulée
    np.random.seed(42)
    volatility = np.std(close) * 0.1
    projected_upper = projected_values + np.random.uniform(0, volatility, days)
    projected_lower = projected_values - np.random.uniform(0, volatility, days)
    
    # Créer le graphique
    fig = go.Figure()
    
    # Données historiques
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['close'],
        name="Historique",
        line=dict(color='black', width=2)
    ))
    
    # Projection
    fig.add_trace(go.Scatter(
        x=future_dates, y=projected_values,
        name="Projection",
        line=dict(color='blue', width=2, dash='dash')
    ))
    
    # Fourchette
    fig.add_trace(go.Scatter(
        x=list(future_dates) + list(future_dates)[::-1],
        y=list(projected_upper) + list(projected_lower)[::-1],
        fill='toself',
        fillcolor='rgba(52, 152, 219, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        name="Fourchette"
    ))
    
    fig.update_layout(
        title=f"Projection des {days} prochains jours",
        yaxis_title="Prix (XOF)",
        xaxis_title="Date",
        template="plotly_white",
        height=400
    )
    
    return fig


# ============================================================================
# PAGES DE L'APPLICATION
# ============================================================================

def page_accueil():
    """Page d'accueil avec résumé du marché."""
    st.header("📊 Tableau de Bord BRVM")
    
    # Rafraîchir les données
    with st.spinner("🔄 Chargement des données..."):
        data = signals.analyze_market()
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    market_summary = data.get("market_summary", {})
    brvm10 = market_summary.get("BRVM10", {})
    brvmac = market_summary.get("BRVMAC", {})
    
    with col1:
        st.metric("BRVM 10", 
                  f"{brvm10.get('value', 'N/A')}", 
                  f"{brvm10.get('change', 0):+.2f}%")
    with col2:
        st.metric("BRVM All-Share", 
                  f"{brvmac.get('value', 'N/A')}",
                  f"{brvmac.get('change', 0):+.2f}%")
    with col3:
        st.metric("Actions Analysées", f"{len(data.get('all_signals', []))}")
    with col4:
        st.metric("Dernière Analyse", 
                  datetime.fromisoformat(data.get('analysis_date', datetime.now().isoformat())).strftime("%H:%M"))
    
    st.divider()
    
    # Top Achat et Top Vente
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔔 Top 5 ACHAT")
        top_buy = data.get("top_buy", [])
        
        for i, s in enumerate(top_buy, 1):
            with st.container():
                st.markdown(f"""
                <div class="recommendation-achat">
                    <b>{i}. {s['ticker']}</b> - Score: {s['overall_score']}<br>
                    <small>Prix: {s.get('price', 0):,.0f} XOF | {s.get('change', 0):+.2f}%</small>
                </div>
                """, unsafe_allow_html=True)
                st.progress(s['overall_score'] / 100)
    
    with col2:
        st.subheader("🔻 Top 5 VENTE")
        top_sell = data.get("top_sell", [])
        
        for i, s in enumerate(top_sell, 1):
            with st.container():
                st.markdown(f"""
                <div class="recommendation-vente">
                    <b>{i}. {s['ticker']}</b> - Score: {s['overall_score']}<br>
                    <small>Prix: {s.get('price', 0):,.0f} XOF | {s.get('change', 0):+.2f}%</small>
                </div>
                """, unsafe_allow_html=True)
                st.progress(s['overall_score'] / 100)
    
    st.divider()
    
    # Tableau des signaux
    st.subheader("📋 Tous les Signaux")
    
    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        filter_rec = st.selectbox("Filtrer par recommandation", 
                                   ["Tous", "ACHAT", "CONSERVER", "NEUTRE", "VENTE"])
    with col2:
        filter_sector = st.selectbox("Filtrer par secteur", ["Tous"] + 
                                       ["Banque", "Assurance", "Industrie", "Services", "Télécom"])
    
    # Préparer le dataframe
    all_signals = data.get("all_signals", [])
    df_signals = pd.DataFrame(all_signals)
    
    if not df_signals.empty:
        # Appliquer les filtres
        if filter_rec != "Tous":
            df_signals = df_signals[df_signals['recommendation'] == filter_rec]
        
        if filter_sector != "Tous":
            df_signals = df_signals[df_signals['fundamental_data'].apply(
                lambda x: x.get('sector') == filter_sector if x else False)]
        
        # Afficher le tableau
        display_cols = ['ticker', 'price', 'change', 'overall_score', 'recommendation']
        st.dataframe(
            df_signals[display_cols].style.format({
                'price': '{:,.0f}',
                'change': '{:+.2f}%',
                'overall_score': '{:.0f}'
            }),
            use_container_width=True,
            height=400
        )


def page_action(ticker: str):
    """Page détaillée pour une action spécifique."""
    st.header(f"📈 Analyse {ticker}")
    
    # Récupérer les données
    signal = signals.get_signal_for_ticker(ticker)
    
    if not signal:
        st.error(f"❌ Aucune donnée trouvée pour {ticker}")
        return
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Prix", f"{signal.get('price', 0):,.0f} XOF", 
                  f"{signal.get('change', 0):+.2f}%")
    with col2:
        score = signal.get('overall_score', 0)
        st.metric("Score Global", f"{score}/100", signal.get('recommendation', ''))
    with col3:
        st.metric("Volume", f"{signal.get('volume', 0):,}")
    with col4:
        fund = signal.get('fundamental_data', {})
        st.metric("Secteur", fund.get('sector', 'N/A'))
    
    st.divider()
    
    # Onglets pour les détails
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Graphiques", "🔧 Signaux Techniques", 
                                      "📈 Fondamentaux", "🔮 Projection"])
    
    with tab1:
        # Générer les données historiques
        current_price = signal.get('price', 3000)
        historical = signals.generate_historical_data(ticker, current_price, 60)
        
        # Sélection de la période
        periode = st.select_slider("Période", 
                                   options=[7, 14, 30, 60, 90],
                                   value=30)
        
        df_period = historical.tail(periode)
        
        # Graphique principal
        fig = plot_candlestick(df_period, ticker)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        # Indicateurs
        show_indicators = st.checkbox("Afficher les indicateurs techniques", value=True)
        if show_indicators:
            fig_indicators = plot_indicators(df_period, ticker)
            if fig_indicators:
                st.plotly_chart(fig_indicators, use_container_width=True)
    
    with tab2:
        st.subheader("🔧 Indicateurs Techniques")
        
        tech = signal.get('technical_signals', {})
        
        # Grille d'indicateurs
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**RSI (14)**")
            st.write(f"Valeur: {tech.get('rsi', 'N/A')}")
            st.write(f"Signal: **{tech.get('rsi_signal', 'N/A')}**")
            
            st.markdown("**Stochastic**")
            st.write(f"%K: {tech.get('stoch_k', 'N/A')}")
            st.write(f"%D: {tech.get('stoch_d', 'N/A')}")
            st.write(f"Signal: **{tech.get('stoch_signal', 'N/A')}**")
        
        with col2:
            st.markdown("**MACD**")
            st.write(f"Ligne MACD: {tech.get('macd', 'N/A')}")
            st.write(f"Signal: **{tech.get('macd_signal', 'N/A')}**")
            
            st.markdown("**Bollinger**")
            st.write(f"Position: **{tech.get('bb_position', 'N/A')}**")
        
        with col3:
            st.markdown("**Moyennes Mobiles**")
            st.write(f"SMA 20: {tech.get('sma_20', 'N/A'):,.0f}")
            st.write(f"SMA 50: {tech.get('sma_50', 'N/A'):,.0f}")
            st.write(f"Signal: **{tech.get('ma_signal', 'N/A')}**")
            
            st.markdown("**Tendance**")
            st.write(f"**{tech.get('trend', 'N/A')}**")
    
    with tab3:
        st.subheader("📈 Données Fondamentales")
        
        fund = signal.get('fundamental_data', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Capitalisation", f"{fund.get('market_cap', 0):,.0f} XOF")
            st.metric("P/E Ratio", f"{fund.get('pe_ratio', 0):.2f}")
            st.metric("Rendement Dividende", f"{fund.get('dividend_yield', 0):.2f}%")
        
        with col2:
            st.metric("ROE", f"{fund.get('roe', 0):.2f}%")
            st.metric("Croissance Revenus", f"{fund.get('revenue_growth', 0):+.2f}%")
            st.metric("Dette/Equity", f"{fund.get('debt_equity', 0):.2f}")
        
        st.divider()
        st.write(f"**Note Analyste:** {fund.get('analyst_rating', 'N/A')}")
        
        # Score fondamental
        fund_score = signal.get('fundamental_score', 0)
        st.progress(fund_score / 100, text=f"Score Fondamental: {fund_score}/100")
    
    with tab4:
        st.subheader("🔮 Projection Future")
        
        # Sélection de la durée
        proj_days = st.slider("Jours de projection", 7, 90, 30)
        
        # Générer la projection
        current_price = signal.get('price', 3000)
        historical = signals.generate_historical_data(ticker, current_price, 60)
        
        fig_proj = plot_projection(historical, proj_days)
        if fig_proj:
            st.plotly_chart(fig_proj, use_container_width=True)
        
        st.warning("⚠️ Les projections sont uniquement informatives et basées sur une tendance linéaire. "
                   "Elles ne constituent pas un conseil financier.")


def page_signaux():
    """Page avec tous les signaux et filtres avancés."""
    st.header("🔍 Analyse Complète")
    
    with st.spinner("Chargement..."):
        data = signals.analyze_market()
    
    all_signals = data.get("all_signals", [])
    df = pd.DataFrame(all_signals)
    
    if df.empty:
        st.error("Aucune donnée disponible")
        return
    
    # Filtres avancés
    st.subheader("🎛️ Filtres")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_score = st.slider("Score minimum", 0, 100, 0)
    with col2:
        max_score = st.slider("Score maximum", 0, 100, 100)
    with col3:
        secteur = st.selectbox("Secteur", ["Tous"] + 
                                ["Banque", "Assurance", "Industrie", "Services", "Télécom"])
    
    # Appliquer les filtres
    df_filtered = df[(df['overall_score'] >= min_score) & (df['overall_score'] <= max_score)]
    
    if secteur != "Tous":
        df_filtered = df_filtered[df_filtered['fundamental_data'].apply(
            lambda x: x.get('sector') == secteur if x else False)]
    
    # Afficher les résultats
    st.write(f"**{len(df_filtered)}** actions correspondent aux filtres")
    
    # Préparer les colonnes à afficher
    display_df = df_filtered[['ticker', 'price', 'change', 'overall_score', 
                              'recommendation', 'fundamental_data']].copy()
    display_df['secteur'] = display_df['fundamental_data'].apply(
        lambda x: x.get('sector', 'N/A') if x else 'N/A')
    display_df = display_df.drop('fundamental_data', axis=1)
    
    # Affichage interactif
    st.dataframe(
        display_df.style.format({
            'price': '{:,.0f}',
            'change': '{:+.2f}%',
            'overall_score': '{:.0f}'
        }),
        use_container_width=True,
        height=500
    )
    
    # Bouton pour voir une action
    st.subheader("🔎 Détail d'une action")
    selected_ticker = st.selectbox("Sélectionner une action", df_filtered['ticker'].tolist())
    if st.button("Voir le détail"):
        st.session_state.page = "action"
        st.session_state.selected_ticker = selected_ticker
        st.rerun()


def page_alertes():
    """Page de configuration et test des alertes."""
    st.header("🔔 Configuration des Alertes")
    
    if not st.session_state.get('is_admin', False):
        st.warning("⚠️ Réservé aux administrateurs")
        return
    
    st.info("📧 Cette page permet de tester l'envoi des alertes. "
            "Configurez les paramètres dans secrets.toml pour la production.")
    
    # Formulaire de test
    with st.form("test_alert"):
        st.subheader("📤 Test d'alerte Email")
        
        col1, col2 = st.columns(2)
        with col1:
            sender_test = st.text_input("Email expéditeur (test)", 
                                        placeholder="your_email@gmail.com")
        with col2:
            password_test = st.text_input("Mot de passe app", type="password",
                                          placeholder="xxxx xxxx xxxx xxxx")
        
        recipients_test = st.text_input("Destinataires (séparés par virgule)",
                                         placeholder="email1@gmail.com, email2@gmail.com")
        
        alert_type = st.radio("Type d'alerte", ["Résumé quotidien", "Action spécifique"])
        
        ticker_alert = None
        if alert_type == "Action spécifique":
            ticker_alert = st.text_input("Code action", placeholder="SIB")
        
        submit_test = st.form_submit_button("📤 Envoyer l'alerte de test")
    
    if submit_test:
        if not sender_test or not password_test or not recipients_test:
            st.error("❌ Veuillez remplir tous les champs")
        else:
            recipients_list = [r.strip() for r in recipients_test.split(",")]
            
            with st.spinner("Envoi en cours..."):
                if alert_type == "Résumé quotidien":
                    success = alerts.send_daily_alert(
                        sender_email=sender_test,
                        sender_password=password_test,
                        recipient_emails=recipients_list,
                        send_even_if_no_change=True
                    )
                else:
                    if not ticker_alert:
                        st.error("❌ Veuillez spécifier un code action")
                    else:
                        success = alerts.send_ticker_alert(
                            ticker=ticker_alert,
                            sender_email=sender_test,
                            sender_password=password_test,
                            recipient_emails=recipients_list
                        )
            
            if success:
                st.success("✅ Alerte envoyée avec succès!")
            else:
                st.error("❌ Échec de l'envoi. Vérifiez les paramètres.")
    
    st.divider()
    
    # Instructions
    st.subheader("📋 Instructions de configuration")
    
    st.markdown("""
    ### Configuration Gmail
    
    1. Allez sur [Google Account](https://myaccount.google.com)
    2. Sécurité → Validation en 2 étapes → Activer
    3. Mots de passe d'application → Créer un mot de passe
    4. Utiliser ce mot de passe dans l'application
    
    ### Configuration Streamlit Cloud
    
    Dans `secrets.toml`:
    ```toml
    [email]
    sender = "your_email@gmail.com"
    password = "your_app_password"
    recipients = ["email1@gmail.com", "email2@gmail.com"]
    alert_time = "17:30"
    ```
    """)


# ============================================================================
# NAVIGATION PRINCIPALE
# ============================================================================

def main():
    """Fonction principale de l'application."""
    
    # Vérifier l'authentification
    if not check_authentication():
        return
    
    # Sidebar - Navigation
    st.sidebar.title("🧭 Navigation")
    
    # Info utilisateur
    st.sidebar.markdown(f"""
    ---
    **Utilisateur:** {st.session_state.username}
    **Rôle:** {'Admin' if st.session_state.is_admin else 'Lecture seule'}
    """)
    
    # Menu de navigation
    pages = {
        "🏠 Accueil": "accueil",
        "🔍 Tous les Signaux": "signaux",
        "🔔 Alertes (Admin)": "alertes"
    }
    
    selected_page = st.sidebar.radio("Aller à", list(pages.keys()))
    
    # Gestion de la page action (sélectionnée depuis une autre page)
    if 'selected_ticker' in st.session_state and 'page' in st.session_state:
        if st.session_state.page == "action":
            page_action(st.session_state.selected_ticker)
            st.session_state.page = None
            return
    
    # Afficher la page sélectionnée
    page_key = pages[selected_page]
    
    if page_key == "accueil":
        page_accueil()
    elif page_key == "signaux":
        page_signaux()
    elif page_key == "alertes":
        page_alertes()
    
    # Bouton de déconnexion
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Déconnexion"):
        logout()
    
    # Footer
    st.sidebar.markdown("""
    ---
    *BRVM Analytics v1.0*
    
    📊 Données: BRVM.org
    
    ℹ️ Les informations sont 
    fournies à titre indicatif.
    """)


if __name__ == "__main__":
    main()
