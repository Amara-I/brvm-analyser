# analyse.py — Version enrichie inspirée du dashboard JSX
import pandas as pd
import numpy as np

# ── BASE DE DONNÉES COMPLÈTE 2015-2026 ──────────────────────────────────────
COMPANIES = [
    {"ticker":"SNTS","name":"Sonatel","country":"Sénégal","sector":"Télécoms","flag":"🇸🇳",
     "per":13.2,"mktcap":1850,
     "prices":{2015:14000,2016:15500,2017:17000,2018:16000,2019:15000,2020:13500,2021:14500,2022:16000,2023:17500,2024:18900,2025:19500,2026:20100},
     "dividends":{2015:1500,2016:1700,2017:1900,2018:1750,2019:1500,2020:1400,2021:1500,2022:1650,2023:1800,2024:1900,2025:1900,2026:1900}},
    {"ticker":"ONTBF","name":"Onatel Burkina","country":"Burkina Faso","sector":"Télécoms","flag":"🇧🇫",
     "per":10.5,"mktcap":320,
     "prices":{2015:4000,2016:5000,2017:6500,2018:7500,2019:9000,2020:10500,2021:12000,2022:14500,2023:17000,2024:19500,2025:21000,2026:21465},
     "dividends":{2015:80,2016:100,2017:130,2018:160,2019:180,2020:200,2021:280,2022:350,2023:430,2024:555,2025:555,2026:555}},
    {"ticker":"BOAB","name":"BOA Bénin","country":"Bénin","sector":"Banques","flag":"🇧🇯",
     "per":9.8,"mktcap":120,
     "prices":{2015:2000,2016:2500,2017:3000,2018:3500,2019:3800,2020:4200,2021:5100,2022:6000,2023:7200,2024:8500,2025:8800,2026:8900},
     "dividends":{2015:80,2016:100,2017:120,2018:150,2019:175,2020:200,2021:270,2022:310,2023:380,2024:468,2025:468,2026:468}},
    {"ticker":"SGBC","name":"SGB CI","country":"Côte d'Ivoire","sector":"Banques","flag":"🇨🇮",
     "per":9.8,"mktcap":590,
     "prices":{2015:3000,2016:3500,2017:4200,2018:4800,2019:5200,2020:5800,2021:6500,2022:7200,2023:8100,2024:9200,2025:9800,2026:10200},
     "dividends":{2015:200,2016:250,2017:300,2018:350,2019:380,2020:400,2021:450,2022:500,2023:560,2024:620,2025:620,2026:620}},
    {"ticker":"CBIBF","name":"Coris Bank","country":"Burkina Faso","sector":"Banques","flag":"🇧🇫",
     "per":8.5,"mktcap":280,
     "prices":{2015:3500,2016:4200,2017:5000,2018:5800,2019:6500,2020:7200,2021:8500,2022:9800,2023:11000,2024:12500,2025:13200,2026:13800},
     "dividends":{2015:150,2016:200,2017:250,2018:300,2019:350,2020:400,2021:500,2022:600,2023:700,2024:800,2025:800,2026:800}},
    {"ticker":"LNBB","name":"Loterie Nat. Bénin","country":"Bénin","sector":"Divertissement","flag":"🇧🇯",
     "per":8.3,"mktcap":45,
     "prices":{2015:0,2016:0,2017:0,2018:0,2019:0,2020:0,2021:0,2022:0,2023:0,2024:3700,2025:3850,2026:3990},
     "dividends":{2015:0,2016:0,2017:0,2018:0,2019:0,2020:0,2021:0,2022:0,2023:220,2024:275,2025:275,2026:275}},
]

YEARS = list(range(2015, 2027))

# ── CALCUL DES MÉTRIQUES ─────────────────────────────────────────────────────
def calc_metrics(company):
    prices = company["prices"]
    dividends = company["dividends"]

    valid_prices = [(y, prices[y]) for y in YEARS if prices[y] > 0]
    if not valid_prices:
        return None

    current_price = valid_prices[-1][1]
    current_div = dividends.get(valid_prices[-1][0], 0)

    # Performance 5 ans
    prices_5 = [(y,p) for y,p in valid_prices if y >= 2021]
    perf5 = round((prices_5[-1][1]/prices_5[0][1]-1)*100, 1) if len(prices_5) >= 2 else None

    # Performance 10 ans
    prices_10 = [(y,p) for y,p in valid_prices if y >= 2016]
    perf10 = round((prices_10[-1][1]/prices_10[0][1]-1)*100, 1) if len(prices_10) >= 2 else None

    # Rendement dividende
    yield_ = round(current_div/current_price*100, 2) if current_price > 0 else 0

    # Dividende moyen
    valid_divs = [dividends[y] for y in YEARS if dividends.get(y,0) > 0]
    avg_div = round(np.mean(valid_divs), 0) if valid_divs else 0

    # Volatilité
    price_vals = [p for _,p in valid_prices]
    returns = [((price_vals[i]-price_vals[i-1])/price_vals[i-1])*100
               for i in range(1, len(price_vals))]
    volat = round(np.std(returns), 1) if len(returns) >= 2 else 0

    risk = "Faible" if volat < 10 else "Moyen" if volat < 20 else "Élevé"

    # SCORE sur 100
    score = 0
    score += min(25, max(0, perf5 or 0) / 2)
    score += min(25, yield_ * 3)
    score += len(valid_divs) / 12 * 20
    per = company.get("per", 15)
    score += 15 if per < 8 else 10 if per < 10 else 6 if per < 12 else 3
    score += 10 if risk == "Faible" else 6 if risk == "Moyen" else 2
    score = min(100, round(score))

    # Signal
    if score >= 80:
        signal, signal_color = "ACHAT FORT", "🟢"
    elif score >= 65:
        signal, signal_color = "ACHAT", "🟩"
    elif score >= 50:
        signal, signal_color = "CONSERVER", "🟡"
    elif score >= 35:
        signal, signal_color = "ALLÉGER", "🟠"
    else:
        signal, signal_color = "VENDRE", "🔴"

    return {
        "perf5": perf5,
        "perf10": perf10,
        "yield_": yield_,
        "avg_div": avg_div,
        "volat": volat,
        "risk": risk,
        "score": score,
        "signal": signal,
        "signal_color": signal_color,
        "current_price": current_price,
        "current_div": current_div,
    }

# ── PROJECTION LINÉAIRE ──────────────────────────────────────────────────────
def project_prices(company, future_years=5):
    prices = company["prices"]
    valid = [(i, prices[y]) for i, y in enumerate(YEARS) if prices[y] > 0]
    if len(valid) < 2:
        return []

    xs = np.array([v[0] for v in valid])
    ys = np.array([v[1] for v in valid])
    m, b = np.polyfit(xs, ys, 1)

    last_idx = valid[-1][0]
    last_year = YEARS[last_idx]

    projections = []
    for i in range(1, future_years + 1):
        projected = max(0, round(b + m * (last_idx + i)))
        projections.append({
            "year": last_year + i,
            "central": projected,
            "optimiste": round(projected * 1.15),
            "pessimiste": round(projected * 0.85),
        })
    return projections

# ── KPIs MARCHÉ GLOBAL ───────────────────────────────────────────────────────
def get_market_kpis():
    total_cap = sum(c["mktcap"] for c in COMPANIES)
    all_metrics = [calc_metrics(c) for c in COMPANIES]
    all_metrics = [m for m in all_metrics if m]

    avg_yield = round(np.mean([m["yield_"] for m in all_metrics]), 2)
    avg_perf5 = round(np.mean([m["perf5"] for m in all_metrics if m["perf5"]]), 1)
    buy_signals = sum(1 for m in all_metrics if m["score"] >= 65)

    return {
        "nb_societes": len(COMPANIES),
        "total_cap": total_cap,
        "avg_yield": avg_yield,
        "avg_perf5": avg_perf5,
        "buy_signals": buy_signals,
    }

# ── CLASSEMENT GÉNÉRAL ───────────────────────────────────────────────────────
def get_ranking():
    ranked = []
    for co in COMPANIES:
        m = calc_metrics(co)
        if m:
            ranked.append({**co, **m})
    return sorted(ranked, key=lambda x: x["score"], reverse=True)
