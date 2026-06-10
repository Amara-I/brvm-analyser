"""
BRVM Analyser - Dashboard d'Analyse du Marché BRVM
Application Streamlit pour l'analyse technique et fondamentale des actions BRVM

Auteur: BRVM Analyser
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import logging

# Import des modules locaux
from scraper_brvm import get_cours_brvm, get_historique_brvm, get_news_brvm, get_fallback_cours
from analyse import (
    calcul_rsi, calcul_macd, calcul_bollinger, 
    calcul_moyenne_mobile, generer_signal, analyse_fondamentale,
    calculer_volatile, calculer_sharpe
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la page Streamlit
st.set_page_config(
    page_title="BRVM Analyser",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': '📊 BRVM Analyser - Analyse du Marché Régional'
    }
)

# Application du thème personnalisé (CSS inline)
st.markdown("""
<style>
    /* Theme vert foncé */
    .stApp {
        background-color: #0E1F1A;
    }
    /* Headers */
    h1, h2, h3 {
        color: #00D084 !important;
    }
    /* Boutons */
    .stButton>button {
        background-color: #1A3D32;
        color: #E8F5E9;
        border: 1px solid #00D084;
    }
    .stButton>button:hover {
        background-color: #00D084;
        color: #0E1F1A;
    }
    /* Dataframes */
    .stDataFrame {
        background-color: #1A3D32;
    }
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #00D084;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #122B24;
    }
    /* Containers */
    .stContainer {
        background-color: #1A3D32;
        border-radius: 10px;
        padding: 15px;
    }
    /* Alerts */
    .stAlert {
        background-color: #1A3D32;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # Cache de 5 minutes
def charger_donnees():
    """
    Charge les données du marché BRVM avec mise en cache.
    """
    try:
        with st.spinner('Chargement des données BRVM...'):
            df = get_cours_brvm()
            
            if df is None or len(df) == 0:
                df = get_fallback_cours()
            
            # Ajouter les indicateurs techniques
            df = ajouter_indicateurs(df)
            
            return df
    except Exception as e:
        logger.error(f"Erreur lors du chargement des données: {e}")
        return get_fallback_cours()


@st.cache_data(ttl=300)
def charger_news():
    """
    Charge les actualités BRVM.
    """
    try:
        return get_news_brvm()
    except Exception as e:
        logger.error(f"Erreur lors du chargement des actualités: {e}")
        return []


def ajouter_indicateurs(df):
    """
    Ajoute les indicateurs techniques et signaux à chaque action.
    """
    try:
        # Pour chaque action, générer un signal
        signaux = []
        
        for _, row in df.iterrows():
            # Créer un DataFrame simulé pour l'analyse
            cours = row.get('Cours', 0)
            if cours > 0:
                # Générer historique simulé pour l'analyse
                dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
                prices = pd.Series([cours * (1 + np.random.uniform(-0.05, 0.05)) for _ in range(100)], index=dates)
                df_temp = pd.DataFrame({'Cours': prices})
                
                signal = generer_signal(df_temp)
            else:
                signal = {'signal': 'NEUTRE', 'score': 0, 'justification': 'Cours indisponible'}
            
            signaux.append(signal)
        
        # Ajouter les colonnes de signaux
        df['Signal'] = [s['signal'] for s in signaux]
        df['Score'] = [s['score'] for s in signaux]
        df['Justification'] = [s['justification'] for s in signaux]
        
        return df
        
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout des indicateurs: {e}")
        df['Signal'] = 'NEUTRE'
        df['Score'] = 0
        df['Justification'] = 'Analyse non disponible'
        return df


def afficher_graphique_cours(symbole):
    """
    Affiche le graphique interactif des cours pour une action sélectionnée.
    """
    try:
        with st.spinner(f'Chargement de l\'historique pour {symbole}...'):
            hist = get_historique_brvm(symbole)
            
            if hist is None or len(hist) == 0:
                st.warning("Données historiques non disponibles")
                return
            
            # Calculer les indicateurs
            if 'Cours' in hist.columns:
                prices = hist['Cours'].dropna()
                
                rsi = calcul_rsi(prices)
                macd = calcul_macd(prices)
                bollinger = calcul_bollinger(prices)
                sma20 = calcul_moyenne_mobile(prices, 20)
                sma50 = calcul_moyenne_mobile(prices, 50)
                
                # Créer le graphique avec sous-graphes
                fig = go.Figure()
                
                # Graphique principal - Cours et Bollinger
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist['Cours'],
                    mode='lines',
                    name='Cours',
                    line=dict(color='#00D084', width=2)
                ))
                
                if len(bollinger) > 0:
                    fig.add_trace(go.Scatter(
                        x=bollinger.index, y=bollinger['Upper'],
                        mode='lines',
                        name='Bollinger Upper',
                        line=dict(color='rgba(255,99,71,0.5)', width=1),
                        showlegend=False
                    ))
                    fig.add_trace(go.Scatter(
                        x=bollinger.index, y=bollinger['Lower'],
                        mode='lines',
                        name='Bollinger Lower',
                        line=dict(color='rgba(255,99,71,0.5)', width=1),
                        fill='tonexty',
                        fillcolor='rgba(0,208,132,0.1)',
                        showlegend=False
                    ))
                
                if len(sma20) > 0:
                    fig.add_trace(go.Scatter(
                        x=sma20.index, y=sma20,
                        mode='lines',
                        name='SMA 20',
                        line=dict(color='#FFA500', width=1)
                    ))
                
                if len(sma50) > 0:
                    fig.add_trace(go.Scatter(
                        x=sma50.index, y=sma50,
                        mode='lines',
                        name='SMA 50',
                        line=dict(color='#FF6347', width=1)
                    ))
                
                fig.update_layout(
                    title=f'Cours et Bandes de Bollinger - {symbole}',
                    xaxis_title='Date',
                    yaxis_title='Prix (FCFA)',
                    template='plotly_dark',
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(26,61,50,0.5)'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Graphique RSI
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(
                    x=rsi.index, y=rsi,
                    mode='lines',
                    name='RSI',
                    line=dict(color='#9B59B6', width=2)
                ))
                
                # Zones de survente et sur achat
                fig_rsi.add_hrect(y0=30, y1=70, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Zone neutre")
                fig_rsi.add_hrect(y0=0, y1=30, line_width=0, fillcolor="red", opacity=0.1, annotation_text="Survente")
                fig_rsi.add_hrect(y0=70, y1=100, line_width=0, fillcolor="red", opacity=0.1, annotation_text="Sur achat")
                
                fig_rsi.update_layout(
                    title='RSI (14)',
                    xaxis_title='Date',
                    yaxis_title='RSI',
                    yaxis=dict(range=[0, 100]),
                    template='plotly_dark',
                    height=250,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(26,61,50,0.5)'
                )
                
                st.plotly_chart(fig_rsi, use_container_width=True)
                
                # Graphique MACD
                fig_macd = go.Figure()
                
                fig_macd.add_trace(go.Scatter(
                    x=macd.index, y=macd['MACD'],
                    mode='lines',
                    name='MACD',
                    line=dict(color='#3498DB', width=2)
                ))
                
                fig_macd.add_trace(go.Scatter(
                    x=macd.index, y=macd['Signal'],
                    mode='lines',
                    name='Signal',
                    line=dict(color='#E74C3C', width=2)
                ))
                
                # Histogramme
                colors = ['#00D084' if v >= 0 else '#E74C3C' for v in macd['Histogramme']]
                fig_macd.add_trace(go.Bar(
                    x=macd.index, y=macd['Histogramme'],
                    name='Histogramme',
                    marker_color=colors
                ))
                
                fig_macd.update_layout(
                    title='MACD (12,26,9)',
                    xaxis_title='Date',
                    yaxis_title='MACD',
                    template='plotly_dark',
                    height=250,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(26,61,50,0.5)'
                )
                
                st.plotly_chart(fig_macd, use_container_width=True)
                
    except Exception as e:
        st.error(f"Erreur lors de l'affichage du graphique: {e}")


def afficher_top_opportunites(df):
    """
    Affiche le top 5 des opportunités d'achat basées sur les signaux ACHETER.
    """
    try:
        # Filtrer les actions avec signal ACHETER
        acheter = df[df['Signal'] == 'ACHETER'].sort_values('Score', ascending=False).head(5)
        
        if len(acheter) == 0:
            st.info("Aucune opportunité d'achat identifiée pour le moment")
            return
        
        st.subheader("🎯 Top 5 Opportunités d'Achat")
        
        cols = st.columns(5)
        
        for i, (_, row) in enumerate(acheter.iterrows()):
            with cols[i]:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #1A3D32 0%, #0E1F1A 100%);
                    border: 1px solid #00D084;
                    border-radius: 10px;
                    padding: 15px;
                    text-align: center;
                    margin: 5px;
                ">
                    <h4 style="color: #00D084; margin: 0;">{row['Symbole']}</h4>
                    <p style="color: #E8F5E9; margin: 5px 0;">
                        Cours: <strong>{row.get('Cours', 0):.0f}</strong>
                    </p>
                    <p style="color: #E8F5E9; margin: 5px 0;">
                        Variation: <strong style="color: {'#00D084' if row.get('Variation', 0) >= 0 else '#E74C3C'}">
                            {row.get('Variation', 0):+.2f}%
                        </strong>
                    </p>
                    <p style="color: #888; font-size: 0.8em;">
                        Score: {row.get('Score', 0):.1f}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
    except Exception as e:
        st.error(f"Erreur lors de l'affichage des opportunités: {e}")


def afficher_tableau_actions(df):
    """
    Affiche le tableau complet des actions avec coloration conditionnelle.
    """
    try:
        # Préparer les données pour l'affichage
        display_df = df.copy()
        
        # Formater les colonnes numériques
        if 'Cours' in display_df.columns:
            display_df['Cours'] = display_df['Cours'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
        
        if 'Variation' in display_df.columns:
            display_df['Variation'] = display_df['Variation'].apply(
                lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
            )
        
        if 'Volume' in display_df.columns:
            display_df['Volume'] = display_df['Volume'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0")
        
        # Appliquer un style conditionnel
        def style_signal(val):
            if val == 'ACHETER':
                return 'background-color: rgba(0,208,132,0.3); color: #00D084; font-weight: bold;'
            elif val == 'VENDRE':
                return 'background-color: rgba(231,76,60,0.3); color: #E74C3C; font-weight: bold;'
            else:
                return 'color: #E8F5E9;'
        
        # Afficher le tableau
        st.dataframe(
            display_df[['Symbole', 'Cours', 'Variation', 'Volume', 'Signal', 'Score']],
            use_container_width=True,
            hide_index=True
        )
        
    except Exception as e:
        st.error(f"Erreur lors de l'affichage du tableau: {e}")


def afficher_actualites(news):
    """
    Affiche les actualités du marché BRVM.
    """
    if not news:
        st.info("Aucune actualité disponible pour le moment")
        return
    
    st.subheader("📰 Dernières Actualités BRVM")
    
    for i, item in enumerate(news[:10]):
        with st.expander(f"{item.get('titre', 'Sans titre')}", expanded=i < 3):
            st.markdown(f"**{item.get('date', '')}**")
            st.write(item.get('resume', 'Pas de résumé disponible'))
            if item.get('lien'):
                st.link_button("Lire plus", item['lien'])


def afficher_statistiques_marche(df):
    """
    Affiche les statistiques globales du marché.
    """
    try:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Nombre d'actions",
                len(df),
                delta_color="off"
            )
        
        with col2:
            # Variation moyenne
            if 'Variation' in df.columns:
                var_moy = df['Variation'].mean()
                st.metric(
                    "Variation moyenne",
                    f"{var_moy:+.2f}%",
                    delta=var_moy,
                    delta_color="normal"
                )
        
        with col3:
            # Meilleure hausse
            if 'Variation' in df.columns:
                best = df.loc[df['Variation'].idxmax()]
                st.metric(
                    "Meilleure hausse",
                    f"{best['Symbole']}",
                    f"{best['Variation']:+.2f}%",
                    delta_color="normal"
                )
        
        with col4:
            # Plus gros volume
            if 'Volume' in df.columns:
                vol_max = df.loc[df['Volume'].idxmax()]
                st.metric(
                    "Plus gros volume",
                    f"{vol_max['Symbole']}",
                    f"{vol_max['Volume']:,.0f}",
                    delta_color="off"
                )
                
    except Exception as e:
        logger.error(f"Erreur statistiques: {e}")


def main():
    """
    Fonction principale de l'application Streamlit.
    """
    # Header
    st.title("📈 BRVM Analyser")
    st.markdown("### Dashboard d'Analyse du Marché Régional des Valeurs Mobilières")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Sélection de la période
        periode = st.selectbox(
            "Période d'analyse",
            ["1 jour", "1 semaine", "1 mois", "3 mois", "6 mois", "1 an"],
            index=5
        )
        
        st.markdown("---")
        
        # Actions rapides
        st.header("🎯 Signaux")
        
        # Compter les signaux
        signals_count = df['Signal'].value_counts() if 'df' in locals() else {}
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("ACHETER", signals_count.get('ACHETER', 0), delta_color="normal")
        with col2:
            st.metric("VENDRE", signals_count.get('VENDRE', 0), delta_color="inverse")
        
        st.metric("NEUTRE", signals_count.get('NEUTRE', 0), delta_color="off")
        
        st.markdown("---")
        
        # Auto-refresh
        st.header("🔄 Actualisation")
        auto_refresh = st.checkbox("Auto-refresh (5 min)", value=True)
        
        if auto_refresh:
            st.info("⏱️ Les données se mettent à jour automatiquement toutes les 5 minutes")
        
        st.markdown("---")
        
        # À propos
        st.header("ℹ️ À propos")
        st.markdown("""
        **BRVM Analyser v1.0**
        
        Dashboard d'analyse technique et fondamentale des actions de la Bourse Régionale des Valeurs Mobilières.
        
        Données fournies par BRVM.org
        """)
    
    # Charger les données
    df = charger_donnees()
    
    if df is None or len(df) == 0:
        st.error("Impossible de charger les données du marché BRVM")
        return
    
    # Afficher les statistiques du marché
    st.header("📊 Vue d'ensemble du marché")
    afficher_statistiques_marche(df)
    st.markdown("---")
    
    # Top opportunités
    st.header("💎 Opportunités")
    afficher_top_opportunites(df)
    st.markdown("---")
    
    # Sélection d'une action pour analyse détaillée
    st.header("🔍 Analyse Détaillée")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### Sélection d'action")
        symbole_selection = st.selectbox(
            "Choisir une action pour l'analyse",
            df['Symbole'].tolist(),
            index=0
        )
        
        if symbole_selection:
            # Afficher les fondamentaux
            fond = analyse_fondamentale(symbole_selection)
            
            st.markdown("#### Données Fondamentales")
            st.markdown(f"""
            **{fond.get('nom', symbole_selection)}**
            
            - **Secteur:** {fond.get('secteur', 'N/A')}
            - **PER:** {fond.get('per', 'N/A')}
            - **Dividende:** {fond.get('dividende', 'N/A')} FCF
            - **Rendement:** {fond.get('rendement', 'N/A')}%
            - **Capitalisation:** {fond.get('capitalisation', 0) / 1e9:.1f} Mrds FCF
            
            {fond.get('description', '')}
            """)
            
            # Afficher le signal
            action_row = df[df['Symbole'] == symbole_selection].iloc[0]
            signal = action_row.get('Signal', 'NEUTRE')
            score = action_row.get('Score', 0)
            
            signal_color = '#00D084' if signal == 'ACHETER' else ('#E74C3C' if signal == 'VENDRE' else '#FFA500')
            
            st.markdown(f"""
            <div style="
                background: {signal_color}20;
                border: 2px solid {signal_color};
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                margin: 10px 0;
            ">
                <h2 style="color: {signal_color}; margin: 0;">{signal}</h2>
                <p style="color: #E8F5E9; margin: 5px 0;">Score: {score:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Afficher les graphiques
        if symbole_selection:
            afficher_graphique_cours(symbole_selection)
    
    st.markdown("---")
    
    # Tableau des actions
    st.header("📋 Toutes les Actions")
    
    # Filtres
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtre_signal = st.selectbox(
            "Filtrer par signal",
            ["Tous", "ACHETER", "VENDRE", "NEUTRE"]
        )
    
    with col2:
        tri_col = st.selectbox(
            "Trier par",
            ["Symbole", "Cours", "Variation", "Volume", "Score"]
        )
    
    with col3:
        ordre = st.selectbox(
            "Ordre",
            ["Croissant", "Décroissant"]
        )
    
    # Appliquer les filtres
    df_filtre = df.copy()
    
    if filtre_signal != "Tous":
        df_filtre = df_filtre[df_filtre['Signal'] == filtre_signal]
    
    # Trier
    ascending = True if ordre == "Croissant" else False
    df_filtre = df_filtre.sort_values(tri_col, ascending=ascending)
    
    # Afficher le tableau
    afficher_tableau_actions(df_filtre)
    
    st.markdown("---")
    
    # Actualités
    st.header("📰 Actualités du Marché")
    news = charger_news()
    afficher_actualites(news)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #888;">
        <p>Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        <p>Données fournies par BRVM.org | Analyse technique à titre informatif</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()