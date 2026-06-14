"""
alerts.py - Système d'alertes BRVM
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

ALERTS_FILE = os.path.join(os.path.dirname(__file__), "cache", "alerts.json")

def load_alerts() -> List[Dict]:
    """Charger les alertes sauvegardées"""
    os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_alerts(alerts: List[Dict]):
    """Sauvegarder les alertes"""
    os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2, default=str)

def add_alert(ticker: str, condition: str, value: float, 
              alert_type: str = "price") -> Dict:
    """Ajouter une nouvelle alerte"""
    alerts = load_alerts()
    alert = {
        "id": int(datetime.now().timestamp()),
        "ticker": ticker,
        "condition": condition,  # "above" ou "below"
        "value": value,
        "type": alert_type,
        "created_at": datetime.now().isoformat(),
        "triggered": False,
        "active": True
    }
    alerts.append(alert)
    save_alerts(alerts)
    return alert

def delete_alert(alert_id: int):
    """Supprimer une alerte"""
    alerts = load_alerts()
    alerts = [a for a in alerts if a.get("id") != alert_id]
    save_alerts(alerts)

def check_alerts(current_prices: Dict) -> List[Dict]:
    """Vérifier si des alertes sont déclenchées"""
    alerts = load_alerts()
    triggered = []

    for alert in alerts:
        if not alert.get("active") or alert.get("triggered"):
            continue

        ticker = alert["ticker"]
        if ticker not in current_prices:
            continue

        price = current_prices[ticker]
        condition = alert["condition"]
        value = alert["value"]

        if condition == "above" and price >= value:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now().isoformat()
            triggered.append(alert)
        elif condition == "below" and price <= value:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now().isoformat()
            triggered.append(alert)

    save_alerts(alerts)
    return triggered

def get_active_alerts() -> List[Dict]:
    """Retourner uniquement les alertes actives non déclenchées"""
    alerts = load_alerts()
    return [a for a in alerts if a.get("active") and not a.get("triggered")]

def get_all_alerts() -> List[Dict]:
    """Retourner toutes les alertes"""
    return load_alerts()
