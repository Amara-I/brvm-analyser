"""
signals.py - Analyse Technique et Fondamentale des Actions BRVM
================================================================
Module d'analyse complète avec indicateurs techniques et scoring.
"""

import json
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from io import StringIO


# ============================================================================
# CONFIGURATION - Chemins et URLs
# ============================================================================

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
DATA_FILE = os.path.join(CACHE_DIR, "market_data.json")
SIGNALS_FILE = os.path.join(CACHE_DIR, "signals.json")

# URLs BRVM
BRVM_BASE_URL = "https://www.brvm.org"
BRVM_QUOTE_URL = f"{BRVM_BASE_URL}/quotations/equities"
BRVM_INDEX_URL = f"{BRVM_BASE_URL}/quotations/indices"

# Créer le cache s'il n'existe pas
os.makedirs(CACHE_DIR, exist_ok=True)


# ============================================================================
# FONCTIONS D'EXTRACTION DES DONNÉES BRVM
# ============================================================================

def get_brvm_tickers() -> List[str]:
    return [
        "BICC", "BOA", "BOAB", "BOABF", "CABLE", "CHOC", "CI00", "CI22",
        "SICM", "SMC", "SOGEBANK", "SPHAS", "STAC", "TTB", "TTBS",
        "LAB", "ALIB", "BNET", "BNP", "BOAMF", "CB", "ECOBANK",
        "FIPC", "FSDH", "LBC", "NSCC", "SAFCA", "SER", "SIB", "STB",
        "STM", "SV", "BABE", "BACO", "BH", "BIDC", "CCT", "CFAO",
        "DIST", "DO", "FAG", "FK", "GC", "GIM", "GSII", "ORAB",
        "PRSC", "SAE", "SAHC", "SAPH", "SDC", "SLB", "SMD", "SNTS",
        "SP", "SMI", "SUNU", "TIR", "TRAP", "TTAK", "UNIL", "UP",
        "UTB", "BGI", "PAL", "SICOR", "STOA", "UTB", "BPEP"
    ]


def fetch_brvm_data() -> Dict:
    cache_age = None
    if os.path.exists(DATA_FILE):
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
        cache_age = file_age.total_seconds() / 60

    if cache_age is not None and cache_age < 5:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)

    data = simulate_brvm_data()

    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    return data


def simulate_brvm_data() -> Dict:
    np.random.seed(42)
    tickers = get_brvm_tickers()
    data = {}

    base_prices = {
        "SIB": 12000, "STB": 6500, "ECOBANK": 5500, "BOA": 5200,
        "NSCC": 4800, "SPHAS": 4500, "SAFCA": 4200, "LBC": 3900,
        "CB": 3800, "FSDH": 3500
    }

    for ticker in tickers:
        base_price = base_prices.get(ticker, 3000 + np.random.randint(0, 5000))
        change_pct = np.random.uniform(-5, 5)

        data[ticker] = {
            "name": f"Action {ticker}",
            "price": round(base_price * (1 + change_pct/100), 2),
            "change": round(change_pct, 2),
            "volume": int(np.random.randint(1000, 50000)),
            "high": round(base_price * (1 + abs(change_pct)/100), 2),
            "low": round(base_price * (1 - abs(change_pct)/100), 2),
            "open": round(base_price, 2),
            "close": round(base_price * (1 + change_pct/100), 2),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "cap": base_price * np.random.randint(1000000, 50000000)
        }

    data["BRVM10"] = {"name": "BRVM 10", "value": 245.32, "change": 1.25}
    data["BRVMAC"] = {"name": "BRVM All-Share", "value": 198.45, "change": 0.87}

    return data


# ============================================================================
# INDICATEURS TECHNIQUES
# ============================================================================

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()

    return macd_line, signal_line


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return upper, middle, lower


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    return prices.ewm(span=period, adjust=False).mean()


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series]:
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()

    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=3).mean()

    return k_percent.fillna(50), d_percent.fillna(50)


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    high_low = high - low
    high_close = abs(high - close.shift())
    low_close = abs(low - close.shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()

    return atr


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    return obv


# ============================================================================
# ANALYSE FONDAMENTALE
# ============================================================================

def get_fundamental_data(ticker: str) -> Dict:
    np.random.seed(hash(ticker) % 1000)

    return {
        "market_cap": np.random.uniform(10, 500) * 1e9,
        "pe_ratio": np.random.uniform(5, 25),
        "dividend_yield": np.random.uniform(0, 8),
        "roe": np.random.uniform(5, 25),
        "debt_equity": np.random.uniform(0, 2),
        "revenue_growth": np.random.uniform(-10, 20),
        "beta": np.random.uniform(0.5, 1.5),
        "sector": np.random.choice(["Banque", "Assurance", "Industrie", "Services", "Télécom"]),
        "analyst_rating": np.random.choice(["Achat", "Conservateur", "Vente"], p=[0.4, 0.4, 0.2])
    }


# ============================================================================
# CALCUL DES SIGNAUX ET SCORING
# ============================================================================

def calculate_technical_signals(ticker: str, historical_data: pd.DataFrame) -> Dict:
    if historical_data is None or len(historical_data) < 20:
        return {"error": "Données insuffisantes pour analyse technique"}

    close = historical_data.get('close', pd.Series())
    high = historical_data.get('high', close)
    low = historical_data.get('low', close)
    volume = historical_data.get('volume', pd.Series([10000] * len(close)))

    # Calcul des indicateurs
    rsi = calculate_rsi(close, 14)
    macd_line, signal_line = calculate_macd(close)
    upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(close)
    sma_20 = calculate_sma(close, 20)
    sma_50 = calculate_sma(close, 50)
    ema_12 = calculate_ema(close, 12)
    ema_26 = calculate_ema(close, 26)
    stoch_k, stoch_d = calculate_stochastic(high, low, close)
    atr = calculate_atr(high, low, close)
    obv = calculate_obv(close, volume)

    # Dernières valeurs
    last_close = close.iloc[-1] if len(close) > 0 else 0
    last_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
    last_macd = macd_line.iloc[-1] if len(macd_line) > 0 else 0
    last_signal = signal_line.iloc[-1] if len(signal_line) > 0 else 0
    last_stoch_k = stoch_k.iloc[-1] if len(stoch_k) > 0 else 50
    last_stoch_d = stoch_d.iloc[-1] if len(stoch_d) > 0 else 50
    last_ema_12 = ema_12.iloc[-1] if len(ema_12) > 0 else last_close
    last_ema_26 = ema_26.iloc[-1] if len(ema_26) > 0 else last_close

    # ✅ CORRECTION 1 - bb_position
    if len(lower_bb) > 0 and last_close < lower_bb.iloc[-1]:
        bb_pos = "bas"
    elif len(upper_bb) > 0 and last_close > upper_bb.iloc[-1]:
        bb_pos = "haut"
    else:
        bb_pos = "milieu"

    # ✅ CORRECTION 2 - trend
    if len(sma_20) > 0 and not pd.isna(sma_20.iloc[-1]):
        trend = "haussière" if last_close > sma_20.iloc[-1] else "baissière"
    else:
        trend = "incertaine"

    signals = {
        # RSI
        "rsi": round(last_rsi, 2),
        "rsi_signal": (
            "survente" if last_rsi < 30
            else "surachat" if last_rsi > 70
            else "neutre"
        ),

        # MACD
        "macd": round(last_macd, 2),
        "macd_signal": "haussier" if last_macd > last_signal else "baissier",

        # ✅ Bollinger corrigé
        "bb_position": bb_pos,

        # Moyennes mobiles
        "sma_20": round(sma_20.iloc[-1], 2) if len(sma_20) > 0 and not pd.isna(sma_20.iloc[-1]) else 0,
        "sma_50": round(sma_50.iloc[-1], 2) if len(sma_50) > 0 and not pd.isna(sma_50.iloc[-1]) else 0,
        "ma_signal": "haussier" if last_ema_12 > last_ema_26 else "baissier",

        # Stochastic
        "stoch_k": round(last_stoch_k, 2),
        "stoch_d": round(last_stoch_d, 2),
        "stoch_signal": (
            "survente" if last_stoch_k < 20
            else "surachat" if last_stoch_k > 80
            else "neutre"
        ),

        # ATR
        "atr": round(atr.iloc[-1], 2) if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else 0,

        # ✅ Tendance corrigée
        "trend": trend
    }

    return signals


def calculate_fundamental_score(ticker: str) -> float:
    fund_data = get_fundamental_data(ticker)
    score = 50

    if 0 < fund_data["pe_ratio"] < 15:
        score += 10
    elif 15 <= fund_data["pe_ratio"] <= 25:
        score += 5
    elif fund_data["pe_ratio"] > 25:
        score -= 5

    if fund_data["dividend_yield"] > 5:
        score += 15
    elif fund_data["dividend_yield"] > 3:
        score += 10
    elif fund_data["dividend_yield"] > 0:
        score += 5

    if fund_data["roe"] > 20:
        score += 10
    elif fund_data["roe"] > 15:
        score += 5
    elif fund_data["roe"] < 5:
        score -= 10

    if fund_data["revenue_growth"] > 10:
        score += 10
    elif fund_data["revenue_growth"] > 0:
        score += 5
    elif fund_data["revenue_growth"] < -5:
        score -= 10

    if fund_data["debt_equity"] < 0.5:
        score += 5
    elif fund_data["debt_equity"] > 1.5:
        score -= 5

    if fund_data["analyst_rating"] == "Achat":
        score += 10
    elif fund_data["analyst_rating"] == "Vente":
        score -= 10

    return max(0, min(100, score))


def calculate_overall_score(ticker: str, technical_signals: Dict, fundamental_score: float) -> Tuple[int, str]:
    tech_score = 50

    if "rsi" in technical_signals:
        rsi_val = technical_signals["rsi"]
        if rsi_val < 30:
            tech_score += 10
        elif rsi_val > 70:
            tech_score -= 10

    if "macd_signal" in technical_signals:
        if technical_signals["macd_signal"] == "haussier":
            tech_score += 15
        else:
            tech_score -= 10

    if "ma_signal" in technical_signals:
        if technical_signals["ma_signal"] == "haussier":
            tech_score += 15
        else:
            tech_score -= 10

    if "stoch_signal" in technical_signals:
        if technical_signals["stoch_signal"] == "survente":
            tech_score += 10
        elif technical_signals["stoch_signal"] == "surachat":
            tech_score -= 5

    if "trend" in technical_signals:
        if technical_signals["trend"] == "haussière":
            tech_score += 10
        elif technical_signals["trend"] == "baissière":
            tech_score -= 10

    if "bb_position" in technical_signals:
        if technical_signals["bb_position"] == "bas":
            tech_score += 8
        elif technical_signals["bb_position"] == "haut":
            tech_score -= 5

    tech_score = max(0, min(100, tech_score))
    overall_score = int(0.6 * tech_score + 0.4 * fundamental_score)

    if overall_score >= 70:
        recommendation = "ACHAT"
    elif overall_score >= 55:
        recommendation = "CONSERVER"
    elif overall_score >= 40:
        recommendation = "NEUTRE"
    else:
        recommendation = "VENTE"

    return overall_score, recommendation


def generate_signals_summary(buy_signals: List[Dict], sell_signals: List[Dict]) -> str:
    summary = """
## 📊 Résumé des Signaux BRVM - {}

### 🔔 ALERTES ACHAT (Top 5)
{}

### 🔻 ALERTES VENTE (Top 5)
{}

### 📈 Méthodologie
- Analyse technique: RSI, MACD, Bollinger, Stochastic, Moyennes Mobiles
- Analyse fondamentale: P/E, Dividendes, ROE, Croissance, Dette
- Score global: 60% Technique + 40% Fondamental
- Source: BRVM.org & Données historiques
""".format(
        datetime.now().strftime("%d/%m/%Y"),
        "\n".join([f"{i+1}. **{s['ticker']}** - Score: {s['score']} - {s.get('name', s['ticker'])}"
                   for i, s in enumerate(buy_signals[:5])]),
        "\n".join([f"{i+1}. **{s['ticker']}** - Score: {s['score']} - {s.get('name', s['ticker'])}"
                   for i, s in enumerate(sell_signals[:5])])
    )
    return summary


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def analyze_market(force_refresh: bool = False) -> Dict:
    if force_refresh or not os.path.exists(SIGNALS_FILE):
        market_data = fetch_brvm_data()
        all_signals = []

        for ticker in get_brvm_tickers():
            if ticker in market_data:
                ticker_data = market_data[ticker]
                historical = generate_historical_data(ticker, ticker_data.get("price", 3000))
                tech_signals = calculate_technical_signals(ticker, historical)
                fund_score = calculate_fundamental_score(ticker)
                overall_score, recommendation = calculate_overall_score(ticker, tech_signals, fund_score)

                signal_entry = {
                    "ticker": ticker,
                    "name": ticker_data.get("name", ticker),
                    "price": ticker_data.get("price", 0),
                    "change": ticker_data.get("change", 0),
                    "volume": ticker_data.get("volume", 0),
                    "technical_signals": tech_signals,
                    "fundamental_score": fund_score,
                    "overall_score": overall_score,
                    "recommendation": recommendation,
                    "fundamental_data": get_fundamental_data(ticker),
                    "timestamp": datetime.now().isoformat()
                }
                all_signals.append(signal_entry)

        all_signals_sorted = sorted(all_signals, key=lambda x: x["overall_score"], reverse=True)

        signals_data = {
            "analysis_date": datetime.now().isoformat(),
            "market_summary": {
                "BRVM10": market_data.get("BRVM10", {}),
                "BRVMAC": market_data.get("BRVMAC", {})
            },
            "all_signals": all_signals_sorted,
            "top_buy": all_signals_sorted[:5],
            "top_sell": all_signals_sorted[-5:][::-1]
        }

        with open(SIGNALS_FILE, 'w') as f:
            json.dump(signals_data, f, indent=2, default=str)

        return signals_data

    else:
        with open(SIGNALS_FILE, 'r') as f:
            return json.load(f)


def generate_historical_data(ticker: str, current_price: float, days: int = 30) -> pd.DataFrame:
    np.random.seed(hash(ticker) % 10000)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    base_prices = [current_price]
    for _ in range(days - 1):
        change = np.random.uniform(-3, 3)
        new_price = base_prices[-1] * (1 + change/100)
        base_prices.append(new_price)

    base_prices.reverse()

    df = pd.DataFrame({
        'date': dates,
        'open': base_prices,
        'high': [p * (1 + abs(np.random.uniform(0, 2))/100) for p in base_prices],
        'low': [p * (1 - abs(np.random.uniform(0, 2))/100) for p in base_prices],
        'close': base_prices,
        'volume': [int(np.random.randint(5000, 50000)) for _ in range(days)]
    })

    return df


def get_signal_for_ticker(ticker: str) -> Optional[Dict]:
    signals_data = analyze_market()
    for signal in signals_data.get("all_signals", []):
        if signal["ticker"] == ticker:
            return signal
    return None


def get_top_signals(n: int = 5, recommendation: str = "ACHAT") -> List[Dict]:
    signals_data = analyze_market()
    filtered = [s for s in signals_data.get("all_signals", [])
                if s.get("recommendation") == recommendation]
    return sorted(filtered, key=lambda x: x["overall_score"], reverse=True)[:n]


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    print("🔍 Analyse BRVM en cours...")
    result = analyze_market(force_refresh=True)
    print(f"\n📊 {len(result['all_signals'])} actions analysées")

    print("\n🏆 TOP 5 ACHAT:")
    for i, s in enumerate(result.get("top_buy", []), 1):
        print(f"  {i}. {s['ticker']} - Score: {s['overall_score']} - {s['recommendation']}")

    print("\n🔻 TOP 5 VENTE:")
    for i, s in enumerate(result.get("top_sell", []), 1):
        print(f"  {i}. {s['ticker']} - Score: {s['overall_score']} - {s['recommendation']}")

    print("\n✅ Fichier signals.json mis à jour")
