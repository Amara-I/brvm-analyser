"""
Module d'analyse technique pour les actions BRVM
Includes RSI, MACD, Bollinger Bands, Moving Averages, et signaux de trading
"""

import pandas as pd
import numpy as np
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calcul_rsi(prices, period=14):
    """
    Calcule l'Indice de Force Relative (RSI).
    
    Args:
        prices: Série pandas des prix de cloture
        period: Période de calcul (défaut: 14)
    
    Returns:
        Série pandas avec les valeurs RSI
    """
    if len(prices) < period + 1:
        return pd.Series([50] * len(prices), index=prices.index)
    
    # Calcul des variations
    delta = prices.diff()
    
    # Séparer gains et pertes
    gains = delta.where(delta > 0, 0)
    losses = (-delta).where(delta < 0, 0)
    
    # Moyennes mobiles exponentielles
    avg_gain = gains.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = losses.ewm(com=period - 1, min_periods=period).mean()
    
    # Calcul du RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calcul_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """
    Calcule le MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: Série pandas des prix de cloture
        fast_period: Période EMA rapide (défaut: 12)
        slow_period: Période EMA lente (défaut: 26)
        signal_period: Période de la ligne de signal (défaut: 9)
    
    Returns:
        DataFrame avec MACD, Signal, et Histogramme
    """
    if len(prices) < slow_period:
        return pd.DataFrame({
            'MACD': [0] * len(prices),
            'Signal': [0] * len(prices),
            'Histogramme': [0] * len(prices)
        }, index=prices.index)
    
    # Calcul des EMAs
    ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
    ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
    
    # MACD = EMA rapide - EMA lente
    macd = ema_fast - ema_slow
    
    # Ligne de signal = EMA du MACD
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    
    # Histogramme = MACD - Signal
    histogram = macd - signal
    
    return pd.DataFrame({
        'MACD': macd,
        'Signal': signal,
        'Histogramme': histogram
    }, index=prices.index)


def calcul_bollinger(prices, period=20, num_std=2):
    """
    Calcule les Bandes de Bollinger.
    
    Args:
        prices: Série pandas des prix de cloture
        period: Période de la moyenne mobile (défaut: 20)
        num_std: Nombre d'écarts-types (défaut: 2)
    
    Returns:
        DataFrame avec Upper, Middle, et Lower bands
    """
    if len(prices) < period:
        middle = prices.rolling(window=period).mean() if len(prices) >= period else prices
        return pd.DataFrame({
            'Upper': middle * 1.02,
            'Middle': middle,
            'Lower': middle * 0.98
        }, index=prices.index)
    
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    return pd.DataFrame({
        'Upper': upper,
        'Middle': middle,
        'Lower': lower
    }, index=prices.index)


def calcul_moyenne_mobile(prices, period):
    """
    Calcule une moyenne mobile simple (SMA).
    
    Args:
        prices: Série pandas des prix de cloture
        period: Période de la moyenne mobile
    
    Returns:
        Série pandas avec les valeurs SMA
    """
    if len(prices) < period:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    
    return prices.rolling(window=period).mean()


def calcul_moyenne_mobile_exponentielle(prices, period):
    """
    Calcule une moyenne mobile exponentielle (EMA).
    
    Args:
        prices: Série pandas des prix de cloture
        period: Période de la moyenne mobile
    
    Returns:
        Série pandas avec les valeurs EMA
    """
    if len(prices) < period:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    
    return prices.ewm(span=period, adjust=False).mean()


def generer_signal(df):
    """
    Génère un signal de trading basé sur l'analyse technique.
    
    Args:
        df: DataFrame avec au moins les colonnes 'Cours' (prix de cloture)
    
    Returns:
        Dict avec 'signal', 'score', et 'justification'
    """
    if df is None or len(df) < 30 or 'Cours' not in df.columns:
        return {
            'signal': 'NEUTRE',
            'score': 0,
            'justification': 'Données insuffisantes pour l\'analyse technique'
        }
    
    try:
        prices = df['Cours'].dropna()
        
        if len(prices) < 30:
            return {
                'signal': 'NEUTRE',
                'score': 0,
                'justification': 'Pas assez de données historiques'
            }
        
        # Calcul des indicateurs
        rsi = calcul_rsi(prices)
        macd = calcul_macd(prices)
        bollinger = calcul_bollinger(prices)
        sma20 = calcul_moyenne_mobile(prices, 20)
        sma50 = calcul_moyenne_mobile(prices, 50)
        
        # Initialisation du score
        score = 0
        justifications = []
        
        # Analyse RSI
        latest_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        if latest_rsi < 30:
            score += 2
            justifications.append(f"RSI en survente ({latest_rsi:.1f})")
        elif latest_rsi > 70:
            score -= 2
            justifications.append(f"RSI en sur achat ({latest_rsi:.1f})")
        elif latest_rsi < 45:
            score += 0.5
            justifications.append(f"RSI proche de la survente ({latest_rsi:.1f})")
        elif latest_rsi > 55:
            score -= 0.5
            justifications.append(f"RSI proche du sur achat ({latest_rsi:.1f})")
        else:
            justifications.append(f"RSI neutre ({latest_rsi:.1f})")
        
        # Analyse MACD
        if len(macd) > 0:
            latest_macd = macd['MACD'].iloc[-1]
            latest_signal = macd['Signal'].iloc[-1]
            
            if not pd.isna(latest_macd) and not pd.isna(latest_signal):
                # Croisement haussier
                if latest_macd > latest_signal and len(macd) > 1:
                    prev_macd = macd['MACD'].iloc[-2]
                    prev_signal = macd['Signal'].iloc[-2]
                    if prev_macd <= prev_signal:
                        score += 2
                        justifications.append("Croisement haussier MACD")
                    else:
                        score += 0.5
                        justifications.append("MACD au-dessus du signal")
                # Croisement baissier
                elif latest_macd < latest_signal and len(macd) > 1:
                    prev_macd = macd['MACD'].iloc[-2]
                    prev_signal = macd['Signal'].iloc[-2]
                    if prev_macd >= prev_signal:
                        score -= 2
                        justifications.append("Croisement baissier MACD")
                    else:
                        score -= 0.5
                        justifications.append("MACD en dessous du signal")
                
                # Histogramme
                latest_hist = macd['Histogramme'].iloc[-1]
                if latest_hist > 0:
                    score += 0.5
                    justifications.append("Histogramme MACD positif")
                else:
                    score -= 0.5
                    justifications.append("Histogramme MACD négatif")
        
        # Analyse Bollinger
        if len(bollinger) > 0:
            latest_price = prices.iloc[-1]
            latest_upper = bollinger['Upper'].iloc[-1]
            latest_lower = bollinger['Lower'].iloc[-1]
            latest_middle = bollinger['Middle'].iloc[-1]
            
            if not pd.isna(latest_upper) and not pd.isna(latest_lower):
                if latest_price < latest_lower:
                    score += 1.5
                    justifications.append("Prix sous la bande inférieure")
                elif latest_price > latest_upper:
                    score -= 1.5
                    justifications.append("Prix au-dessus de la bande supérieure")
                
                # Position relative
                position_pct = (latest_price - latest_lower) / (latest_upper - latest_lower) if (latest_upper - latest_lower) > 0 else 0.5
                if position_pct < 0.2:
                    score += 1
                    justifications.append("Prix proche de la bande inférieure")
                elif position_pct > 0.8:
                    score -= 1
                    justifications.append("Prix proche de la bande supérieure")
        
        # Analyse des moyennes mobiles
        if len(sma20) > 0 and len(sma50) > 0:
            latest_sma20 = sma20.iloc[-1]
            latest_sma50 = sma50.iloc[-1]
            latest_price = prices.iloc[-1]
            
            if not pd.isna(latest_sma20) and not pd.isna(latest_sma50):
                # Tendance haussière (prix > SMA20 > SMA50)
                if latest_price > latest_sma20 > latest_sma50:
                    score += 1.5
                    justifications.append("Tendance haussière (prix > SMA20 > SMA50)")
                # Tendance baissière (prix < SMA20 < SMA50)
                elif latest_price < latest_sma20 < latest_sma50:
                    score -= 1.5
                    justifications.append("Tendance baissière (prix < SMA20 < SMA50)")
                # Croisement
                elif len(sma20) > 1:
                    prev_sma20 = sma20.iloc[-2]
                    prev_sma50 = sma50.iloc[-2]
                    if not pd.isna(prev_sma20) and not pd.isna(prev_sma50):
                        if prev_sma20 <= prev_sma50 and latest_sma20 > latest_sma50:
                            score += 1
                            justifications.append("Croisement haussier SMA20/SMA50")
                        elif prev_sma20 >= prev_sma50 and latest_sma20 < latest_sma50:
                            score -= 1
                            justifications.append("Croisement baissier SMA20/SMA50")
        
        # Analyse de la variation récente
        if len(prices) >= 5:
            variation_5j = (prices.iloc[-1] - prices.iloc[-5]) / prices.iloc[-5] * 100
            if variation_5j > 5:
                score -= 1
                justifications.append(f"Haute variation récente (+{variation_5j:.1f}% en 5 jours)")
            elif variation_5j < -5:
                score += 1
                justifications.append(f"Bas de variation récente ({variation_5j:.1f}% en 5 jours)")
        
        # Détermination du signal final
        if score >= 2:
            signal = "ACHETER"
        elif score <= -2:
            signal = "VENDRE"
        else:
            signal = "NEUTRE"
        
        justification = ". ".join(justifications[:4]) if justifications else "Analyse technique neutre"
        
        return {
            'signal': signal,
            'score': round(score, 2),
            'justification': justification
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du signal: {e}")
        return {
            'signal': 'NEUTRE',
            'score': 0,
            'justification': f"Erreur d'analyse: {str(e)}"
        }


def analyse_fondamentale(symbole):
    """
    Retourne les données fondamentales approximatives pour une action.
    En l'absence de données temps réel, des estimations basées sur le secteur sont retournées.
    
    Args:
        symbole: Symbole de l'action
    
    Returns:
        Dict avec les données fondamentales
    """
    # Données fondamentales approximatives basées sur les secteurs
    fondamentaux = {
        'BACC.CI': {
            'nom': 'Bank of Africa Côte d\'Ivoire',
            'secteur': 'Banque',
            'per': 12.5,
            'dividende': 450,
            'rendement': 5.3,
            'capitalisation': 185000000000,
            'description': 'Première banque privée de Côte d\'Ivoire'
        },
        'BRVM.AO': {
            'nom': 'Bourse Régionale des Valeurs Mobilières',
            'secteur': 'Finance',
            'per': 18.2,
            'dividende': 120,
            'rendement': 4.9,
            'capitalisation': 45000000000,
            'description': 'Société de Bourse Régionale'
        },
        'BRVM.CI': {
            'nom': 'BRVM Composite Index',
            'secteur': 'Indice',
            'per': 0,
            'dividende': 0,
            'rendement': 0,
            'capitalisation': 0,
            'description': 'Indice Composite de la BRVM'
        },
        'BOA.ML': {
            'nom': 'Bank of Africa Mali',
            'secteur': 'Banque',
            'per': 10.8,
            'dividende': 380,
            'rendement': 6.2,
            'capitalisation': 95000000000,
            'description': 'Filiale Bank of Africa au Mali'
        },
        'SONA.CI': {
            'nom': 'Société d\'Eau et d\'Electricité de Côte d\'Ivoire',
            'secteur': 'Service public',
            'per': 14.3,
            'dividende': 520,
            'rendement': 5.7,
            'capitalisation': 210000000000,
            'description': 'Distribution d\'eau et d\'électricité'
        },
        'SMB.CI': {
            'nom': 'Société Minière de Côte d\'Ivoire',
            'secteur': 'Mines',
            'per': 8.5,
            'dividende': 150,
            'rendement': 4.8,
            'capitalisation': 65000000000,
            'description': 'Exploitation minière aurifère'
        },
        'TTR.SN': {
            'nom': 'TotalEnergies Sénégal',
            'secteur': 'Énergie',
            'per': 11.2,
            'dividende': 2100,
            'rendement': 5.0,
            'capitalisation': 380000000000,
            'description': 'Distribution de produits pétroliers'
        },
        'SIC.CI': {
            'nom': 'Société Ivorienne de Construction',
            'secteur': 'Bâtiment',
            'per': 9.8,
            'dividende': 350,
            'rendement': 4.9,
            'capitalisation': 78000000000,
            'description': 'Bâtiment et travaux publics'
        },
        'SEDACI': {
            'nom': 'Société d\'Exploitation du District d\'Abidjan',
            'secteur': 'Transport',
            'per': 15.5,
            'dividende': 280,
            'rendement': 6.8,
            'capitalisation': 42000000000,
            'description': 'Transport urbain'
        },
    }
    
    # Retourner les données si elles existent, sinon données génériques
    if symbole in fondamentaux:
        return fondamentaux[symbole]
    
    # Retourner des données génériques basées sur le préfixe
    if symbole.startswith('BOA'):
        return {
            'nom': symbole,
            'secteur': 'Banque',
            'per': 11.5,
            'dividende': 350,
            'rendement': 5.5,
            'capitalisation': 100000000000,
            'description': 'Banque régionale'
        }
    elif symbole.startswith('BRVM'):
        return {
            'nom': symbole,
            'secteur': 'Finance',
            'per': 15.0,
            'dividende': 200,
            'rendement': 4.5,
            'capitalisation': 50000000000,
            'description': 'Société de financement'
        }
    elif '.CI' in symbole:
        return {
            'nom': symbole,
            'secteur': 'Services',
            'per': 12.0,
            'dividende': 250,
            'rendement': 4.2,
            'capitalisation': 75000000000,
            'description': 'Entreprise cotée Côte d\'Ivoire'
        }
    elif '.ML' in symbole:
        return {
            'nom': symbole,
            'secteur': 'Services',
            'per': 10.5,
            'dividende': 300,
            'rendement': 5.0,
            'capitalisation': 80000000000,
            'description': 'Entreprise cotée Mali'
        }
    elif '.SN' in symbole:
        return {
            'nom': symbole,
            'secteur': 'Services',
            'per': 13.0,
            'dividende': 400,
            'rendement': 4.8,
            'capitalisation': 150000000000,
            'description': 'Entreprise cotée Sénégal'
        }
    elif '.TG' in symbole:
        return {
            'nom': symbole,
            'secteur': 'Services',
            'per': 11.0,
            'dividende': 280,
            'rendement': 4.5,
            'capitalisation': 60000000000,
            'description': 'Entreprise cotée Togo'
        }
    elif '.BF' in symbole:
        return {
            'nom': symbole,
            'secteur': 'Services',
            'per': 10.0,
            'dividende': 320,
            'rendement': 5.2,
            'capitalisation': 55000000000,
            'description': 'Entreprise cotée Burkina'
        }
    else:
        return {
            'nom': symbole,
            'secteur': 'Services',
            'per': 12.0,
            'dividende': 250,
            'rendement': 4.5,
            'capitalisation': 70000000000,
            'description': 'Action BRVM'
        }


def calculer_volatile(historique):
    """
    Calcule la volatilité historique d'une action.
    
    Args:
        historique: DataFrame avec les prix
    
    Returns:
        Float avec la volatilité annualisée en pourcentage
    """
    if historique is None or len(historique) < 2 or 'Cours' not in historique.columns:
        return 0
    
    try:
        returns = historique['Cours'].pct_change().dropna()
        volatile = returns.std() * np.sqrt(252) * 100  # Annualisation
        return round(volatile, 2)
    except:
        return 0


def calculer_sharpe(historique, taux_risk_free=0.05):
    """
    Calcule le ratio de Sharpe.
    
    Args:
        historique: DataFrame avec les prix
        taux_risk_free: Taux sans risque (défaut: 5%)
    
    Returns:
        Float avec le ratio de Sharpe
    """
    if historique is None or len(historique) < 2 or 'Cours' not in historique.columns:
        return 0
    
    try:
        returns = historique['Cours'].pct_change().dropna()
        excess_return = returns.mean() * 252 - taux_risk_free
        volatility = returns.std() * np.sqrt(252)
        
        if volatility > 0:
            sharpe = excess_return / volatility
            return round(sharpe, 2)
        return 0
    except:
        return 0


if __name__ == "__main__":
    # Test du module d'analyse
    print("Test du module d'analyse...")
    
    # Créer des données de test
    dates = pd.date_range(start='2025-01-01', end='2026-06-01', freq='D')
    prices = pd.Series(np.random.uniform(1000, 5000, len(dates)), index=dates)
    
    # Test RSI
    rsi = calcul_rsi(prices)
    print(f"RSI moyen: {rsi.mean():.2f}")
    
    # Test MACD
    macd = calcul_macd(prices)
    print(f"MACD: OK")
    
    # Test Bollinger
    bollinger = calcul_bollinger(prices)
    print(f"Bollinger: OK")
    
    # Test signal
    test_df = pd.DataFrame({'Cours': prices})
    signal = generer_signal(test_df)
    print(f"Signal: {signal['signal']} (score: {signal['score']})")
    
    # Test fondamentaux
    fondamentaux = analyse_fondamentale('BACC.CI')
    print(f"Fondamentaux BACC.CI: PER={fondamentaux['per']}, Dividende={fondamentaux['dividende']}")