import pandas as pd
import numpy as np
import pandas_ta as ta

def build_dataframe(historique):
    """Construit un DataFrame OHLCV depuis l'historique"""
    if not historique:
        return None
    df = pd.DataFrame(historique)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    return df

def add_indicators(df):
    """Ajoute tous les indicateurs techniques"""
    if df is None or len(df) < 20:
        return df
    
    # ── Moyennes mobiles
    df["MA20"]  = ta.sma(df["close"], length=20)
    df["MA50"]  = ta.sma(df["close"], length=50)
    df["MA200"] = ta.sma(df["close"], length=200)
    df["EMA20"] = ta.ema(df["close"], length=20)
    df["EMA50"] = ta.ema(df["close"], length=50)
    
    # ── RSI
    df["RSI"] = ta.rsi(df["close"], length=14)
    
    # ── MACD
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None:
        df["MACD"]        = macd["MACD_12_26_9"]
        df["MACD_signal"] = macd["MACDs_12_26_9"]
        df["MACD_hist"]   = macd["MACDh_12_26_9"]
    
    # ── Bollinger Bands
    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None:
        df["BB_upper"] = bb[f"BBU_20_2.0"]
        df["BB_mid"]   = bb[f"BBM_20_2.0"]
        df["BB_lower"] = bb[f"BBL_20_2.0"]
    
    # ── Stochastique
    stoch = ta.stoch(df["high"], df["low"], df["close"])
    if stoch is not None:
        df["STOCH_K"] = stoch["STOCHk_14_3_3"]
        df["STOCH_D"] = stoch["STOCHd_14_3_3"]
    
    # ── ATR (volatilité)
    df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    
    # ── Volume moyen
    df["VOL_MA20"] = ta.sma(df["volume"], length=20)
    
    return df

def generate_signal(df, company_info):
    """
    Génère un signal de trading composite
    Retourne un dict avec score, signal, résumé
    """
    if df is None or len(df) < 30:
        return {"score": 0, "signal": "DONNÉES INSUFFISANTES", "color": "#6B7280", "resume": "Historique trop court."}
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    score = 0
    points = []
    
    # ── 1. TENDANCE (30 pts max)
    if pd.notna(last.get("MA20")) and pd.notna(last.get("MA50")):
        if last["close"] > last["MA50"]:
            score += 10
            points.append("✅ Prix au-dessus MA50")
        else:
            score -= 5
            points.append("⚠️ Prix sous MA50")
        
        if pd.notna(last.get("MA200")):
            if last["close"] > last["MA200"]:
                score += 10
                points.append("✅ Prix au-dessus MA200 (tendance haussière LT)")
            else:
                points.append("❌ Prix sous MA200 (tendance baissière LT)")
        
        if last["MA20"] > last["MA50"]:
            score += 10
            points.append("✅ MA20 > MA50 (Golden Cross)")
        else:
            score -= 5
            points.append("❌ MA20 < MA50 (Death Cross)")
    
    # ── 2. RSI (20 pts max)
    if pd.notna(last.get("RSI")):
        rsi = last["RSI"]
        if 40 <= rsi <= 60:
            score += 10
            points.append(f"✅ RSI neutre ({rsi:.1f})")
        elif rsi < 30:
            score += 20
            points.append(f"🔥 RSI survendu ({rsi:.1f}) — Signal ACHAT fort")
        elif rsi > 70:
            score -= 10
            points.append(f"⚠️ RSI suracheté ({rsi:.1f}) — Prudence")
        elif 30 <= rsi < 40:
            score += 15
            points.append(f"✅ RSI en zone d'achat ({rsi:.1f})")
    
    # ── 3. MACD (20 pts max)
    if pd.notna(last.get("MACD")) and pd.notna(last.get("MACD_signal")):
        if last["MACD"] > last["MACD_signal"]:
            score += 10
            points.append("✅ MACD haussier")
        else:
            score -= 5
            points.append("❌ MACD baissier")
        
        if pd.notna(prev.get("MACD")) and pd.notna(prev.get("MACD_signal")):
            if prev["MACD"] < prev["MACD_signal"] and last["MACD"] > last["MACD_signal"]:
                score += 10
                points.append("🔥 Croisement MACD haussier (signal fort)")
            elif prev["MACD"] > prev["MACD_signal"] and last["MACD"] < last["MACD_signal"]:
                score -= 10
                points.append("🔴 Croisement MACD baissier (signal vente)")
    
    # ── 4. BOLLINGER (15 pts max)
    if pd.notna(last.get("BB_lower")) and pd.notna(last.get("BB_upper")):
        if last["close"] <= last["BB_lower"]:
            score += 15
            points.append("🔥 Prix sur bande Bollinger basse — Rebond possible")
        elif last["close"] >= last["BB_upper"]:
            score -= 10
            points.append("⚠️ Prix sur bande Bollinger haute — Résistance")
        else:
            score += 5
            points.append("✅ Prix dans les bandes Bollinger")
    
    # ── 5. STOCHASTIQUE (15 pts max)
    if pd.notna(last.get("STOCH_K")):
        k = last["STOCH_K"]
        if k < 20:
            score += 15
            points.append(f"🔥 Stochastique survendu ({k:.1f})")
        elif k > 80:
            score -= 10
            points.append(f"⚠️ Stochastique suracheté ({k:.1f})")
        else:
            score += 5
    
    # ── FONDAMENTAUX (bonus)
    fond = company_info.get("fondamentaux", {})
    per = fond.get("per", company_info.get("per", None))
    if per:
        if per < 8:
            score += 10
            points.append(f"✅ PER attractif ({per:.1f})")
        elif per < 12:
            score += 5
            points.append(f"✅ PER raisonnable ({per:.1f})")
        elif per > 20:
            score -= 5
            points.append(f"⚠️ PER élevé ({per:.1f})")
    
    # Normaliser score 0-100
    score = max(0, min(100, score + 50))
    
    # ── Déterminer signal
    if score >= 80:
        signal = "ACHAT FORT"
        color = "#22C55E"
        emoji = "🟢"
    elif score >= 65:
        signal = "ACHAT"
        color = "#84CC16"
        emoji = "🟩"
    elif score >= 50:
        signal = "CONSERVER"
        color = "#D4A843"
        emoji = "🟡"
    elif score >= 35:
        signal = "ALLÉGER"
        color = "#F97316"
        emoji = "🟠"
    else:
        signal = "VENDRE"
        color = "#EF4444"
        emoji = "🔴"
    
    # ── Résumé automatique
    resume = f"{emoji} **{signal}** (Score: {score}/100)\n\n"
    resume += "\n".join(points[:6])
    
    return {
        "score": score,
        "signal": signal,
        "color": color,
        "emoji": emoji,
        "resume": resume,
        "points": points,
        "last_rsi": float(last.get("RSI", 0) or 0),
        "last_macd": float(last.get("MACD", 0) or 0),
        "last_close": float(last.get("close", 0) or 0),
    }

def get_top5(all_signals):
    """Retourne top 5 achat et top 5 vente"""
    sorted_sigs = sorted(all_signals.items(), key=lambda x: x[1]["score"], reverse=True)
    top_buy  = [(t, s) for t, s in sorted_sigs if s["score"] >= 50][:5]
    top_sell = [(t, s) for t, s in sorted_sigs if s["score"] < 50][-5:]
    return top_buy, top_sell[::-1]
