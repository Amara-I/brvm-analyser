import requests
from bs4 import BeautifulSoup
import pandas as pd
import json, os, time
from datetime import datetime, timedelta
import feedparser

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

CACHE_FILE = "data/historique.json"
CACHE_DURATION_HOURS = 24

# ── LISTE COMPLÈTE 47 ACTIONS BRVM ──────────────────────────────────────────
TICKERS_BRVM = [
    # Télécoms
    {"ticker":"SNTS","name":"Sonatel","sector":"Télécoms","country":"Sénégal","flag":"🇸🇳"},
    {"ticker":"ONTBF","name":"Onatel Burkina","sector":"Télécoms","country":"Burkina Faso","flag":"🇧🇫"},
    {"ticker":"CÔTE","name":"CIE","sector":"Energie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    # Banques
    {"ticker":"SGBC","name":"SGB CI","sector":"Banques","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"ETIT","name":"Ecobank TI","sector":"Banques","country":"Togo","flag":"🇹🇬"},
    {"ticker":"BOAB","name":"BOA Bénin","sector":"Banques","country":"Bénin","flag":"🇧🇯"},
    {"ticker":"BOABF","name":"BOA Burkina","sector":"Banques","country":"Burkina Faso","flag":"🇧🇫"},
    {"ticker":"BOAC","name":"BOA Côte d'Ivoire","sector":"Banques","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"BOAM","name":"BOA Mali","sector":"Banques","country":"Mali","flag":"🇲🇱"},
    {"ticker":"BOAN","name":"BOA Niger","sector":"Banques","country":"Niger","flag":"🇳🇪"},
    {"ticker":"BOAS","name":"BOA Sénégal","sector":"Banques","country":"Sénégal","flag":"🇸🇳"},
    {"ticker":"CBIBF","name":"Coris Bank","sector":"Banques","country":"Burkina Faso","flag":"🇧🇫"},
    {"ticker":"BICB","name":"BIC Bénin","sector":"Banques","country":"Bénin","flag":"🇧🇯"},
    {"ticker":"BICC","name":"BIC CI","sector":"Banques","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"NSBC","name":"NSIA Banque CI","sector":"Banques","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"ORGT","name":"Oragroup Togo","sector":"Banques","country":"Togo","flag":"🇹🇬"},
    {"ticker":"SIBC","name":"SIB CI","sector":"Banques","country":"Côte d'Ivoire","flag":"🇨🇮"},
    # Industrie
    {"ticker":"STBC","name":"SOLIBRA CI","sector":"Industrie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SMBC","name":"SMB CI","sector":"Industrie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"TTLC","name":"TOTAL CI","sector":"Energie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"TTLS","name":"TOTAL Sénégal","sector":"Energie","country":"Sénégal","flag":"🇸🇳"},
    {"ticker":"PRSC","name":"TRACTAFRIC","sector":"Industrie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"ABJC","name":"MOVIS CI","sector":"Transport","country":"Côte d'Ivoire","flag":"🇨🇮"},
    # Agriculture
    {"ticker":"PALC","name":"PALM CI","sector":"Agriculture","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SICC","name":"SICOR CI","sector":"Agriculture","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SOGC","name":"SOGB CI","sector":"Agriculture","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SPHC","name":"SAPH CI","sector":"Agriculture","country":"Côte d'Ivoire","flag":"🇨🇮"},
    # Distribution
    {"ticker":"CFAC","name":"CFAO CI","sector":"Distribution","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SDCC","name":"SDCI","sector":"Distribution","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SHEC","name":"SHELL CI","sector":"Energie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    # Assurance
    {"ticker":"GNSC","name":"GNSS CI","sector":"Assurance","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"NSIA","name":"NSIA CI","sector":"Assurance","country":"Côte d'Ivoire","flag":"🇨🇮"},
    # Autres
    {"ticker":"LNBB","name":"Loterie Bénin","sector":"Divertissement","country":"Bénin","flag":"🇧🇯"},
    {"ticker":"CABC","name":"Sucrivoire CI","sector":"Agro-industrie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"NEIC","name":"NEI-CEDA CI","sector":"Edition","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SVOC","name":"SIVOA CI","sector":"Agro-industrie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"FTSC","name":"Filtisac CI","sector":"Industrie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"CIEC","name":"CIE CI","sector":"Energie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SEMC","name":"SETAO CI","sector":"BTP","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"UNXC","name":"UNIWAX CI","sector":"Textile","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"UNLC","name":"UNILEVER CI","sector":"Distribution","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SLBC","name":"SOLIBRA","sector":"Industrie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SCRC","name":"SUCRIVOIRE","sector":"Agro-industrie","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"BNBC","name":"BICI CI","sector":"Banques","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"SAFC","name":"SAFCA CI","sector":"Finance","country":"Côte d'Ivoire","flag":"🇨🇮"},
    {"ticker":"STAC","name":"SETACI","sector":"BTP","country":"Côte d'Ivoire","flag":"🇨🇮"},
]

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(data):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cache_is_fresh():
    if not os.path.exists(CACHE_FILE):
        return False
    mtime = os.path.getmtime(CACHE_FILE)
    age = time.time() - mtime
    return age < CACHE_DURATION_HOURS * 3600

def scrape_brvm_cours():
    """Scrape cours depuis brvm.org"""
    try:
        url = "https://www.brvm.org/fr/cours-actions/0/all"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("table tbody tr")
        data = {}
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                ticker = cols[0].text.strip()
                try:
                    close = float(cols[3].text.strip().replace(" ","").replace(",","."))
                    variation = cols[4].text.strip()
                    volume = cols[5].text.strip() if len(cols) > 5 else "0"
                    data[ticker] = {
                        "close": close,
                        "variation": variation,
                        "volume": volume,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                except:
                    continue
        return data
    except Exception as e:
        print(f"Erreur scraping BRVM: {e}")
        return {}

def scrape_sika_historique(ticker, years=10):
    """Scrape historique depuis sikafinance.com"""
    try:
        url = f"https://www.sikafinance.com/marches/historique/{ticker}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("table tbody tr")
        historique = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                try:
                    date_str = cols[0].text.strip()
                    close = float(cols[1].text.strip().replace(" ","").replace(",","."))
                    open_ = float(cols[2].text.strip().replace(" ","").replace(",",".")) if cols[2].text.strip() else close
                    high = float(cols[3].text.strip().replace(" ","").replace(",",".")) if cols[3].text.strip() else close
                    low = float(cols[4].text.strip().replace(" ","").replace(",",".")) if len(cols) > 4 and cols[4].text.strip() else close
                    volume = int(cols[5].text.strip().replace(" ","").replace(",","")) if len(cols) > 5 and cols[5].text.strip().isdigit() else 0
                    historique.append({
                        "date": date_str,
                        "open": open_,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume
                    })
                except:
                    continue
        return historique
    except Exception as e:
        print(f"Erreur scraping Sika {ticker}: {e}")
        return []

def scrape_sika_fondamentaux(ticker):
    """Scrape données fondamentales depuis sikafinance.com"""
    try:
        url = f"https://www.sikafinance.com/marches/fichevaleur/{ticker}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        data = {}
        tables = soup.select("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all(["td","th"])
                if len(cols) >= 2:
                    key = cols[0].text.strip().lower()
                    val = cols[1].text.strip()
                    if "per" in key or "p/e" in key:
                        try: data["per"] = float(val.replace(",","."))
                        except: pass
                    elif "capitalisation" in key:
                        try: data["mktcap"] = val
                        except: pass
                    elif "dividende" in key:
                        try: data["dividende"] = float(val.replace(",",".").replace(" ",""))
                        except: pass
                    elif "bénéfice" in key or "benefice" in key:
                        try: data["benefice"] = val
                        except: pass
                    elif "chiffre" in key:
                        try: data["ca"] = val
                        except: pass
        return data
    except Exception as e:
        print(f"Erreur fondamentaux {ticker}: {e}")
        return {}

def get_news_brvm():
    """Récupère actualités BRVM"""
    news = []
    feeds = [
        "https://www.sikafinance.com/rss",
        "https://www.brvm.org/rss.xml",
        "https://www.agenceecofin.com/rss/bourse",
    ]
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                news.append({
                    "title": entry.get("title",""),
                    "link": entry.get("link",""),
                    "date": entry.get("published",""),
                    "source": feed_url.split("/")[2]
                })
        except:
            continue
    return news[:15]

def get_all_data(force_refresh=False):
    """Point d'entrée principal — retourne toutes les données"""
    if not force_refresh and cache_is_fresh():
        return load_cache()
    
    print("Scraping données BRVM...")
    cours_live = scrape_brvm_cours()
    
    all_data = {}
    for company in TICKERS_BRVM:
        t = company["ticker"]
        historique = scrape_sika_historique(t)
        fondamentaux = scrape_sika_fondamentaux(t)
        
        all_data[t] = {
            **company,
            "cours_live": cours_live.get(t, {}),
            "historique": historique,
            "fondamentaux": fondamentaux,
            "last_update": datetime.now().isoformat()
        }
        time.sleep(0.5)  # Respecter le serveur
    
    all_data["_news"] = get_news_brvm()
    all_data["_last_update"] = datetime.now().isoformat()
    
    save_cache(all_data)
    return all_data
