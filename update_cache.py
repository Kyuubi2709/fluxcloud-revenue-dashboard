import os
import json
import time
import requests
import re

from analyze_fluxcloud import API_URL as APPS_API_URL  # existing import

# Existing APIs
NODES_API_URL = "https://api.runonflux.io/daemon/viewdeterministicfluxnodelist"
LOCATIONS_API_URL = "https://api.runonflux.io/apps/locations"

# Permanent messages endpoint (per app)
PERM_MSG_API_URL = "https://api.runonflux.io/apps/permanentmessages"

# Explorer endpoint for wallet tx history (FIAT wallet classification)
EXPLORER_TX_API_URL = "https://api.runonflux.io/explorer/transactions"

# FIAT wallet address used by your company for credit card / PayPal sales
FIAT_WALLET_ADDRESS = "t1XktDZ9Z1QiefMYE5nMFohe8VG2c2BD5A5"

# Paths
CACHE_DIR = "/app/cache"
CACHE_FILE = os.path.join(CACHE_DIR, "stats.json")
PERM_MSG_DIR = os.path.join(CACHE_DIR, "permanent_messages")
PRICE_FILE = os.path.join(os.path.dirname(__file__), "price.json")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(PERM_MSG_DIR, exist_ok=True)


def fetch_apps():
    resp = requests.get(APPS_API_URL, timeout=25)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def fetch_nodes():
    try:
        resp = requests.get(NODES_API_URL, timeout=25)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:
        return []


def fetch_locations():
    """Fetch running app locations (each entry is one running instance on a node)."""
    try:
        resp = requests.get(LOCATIONS_API_URL, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except Exception:
        return []


def safe_filename(name: str) -> str:
    """Make app name safe as a filename."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def fetch_permanent_messages_for_app(app_name: str):
    """
    Fetch permanent messages for a single app and cache them under
    /app/cache/permanent_messages/<SAFE_APPNAME>.json
    """
    params = {"appname": app_name}
    path = os.path.join(PERM_MSG_DIR, f"{safe_filename(app_name)}.json")

    try:
        resp = requests.get(PERM_MSG_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception:
        # If API fails, try to fall back to cached file
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    # Write / refresh cache file
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        # If write fails, just keep going
        pass

    return data


def load_permanent_messages_for_apps(apps):
    """
    For all current live apps (from globalappsspecifications), fetch
    their permanent messages and return a dict:
        { app_name: [msg1, msg2, ...], ... }
    """
    perm_messages = {}

    for app in apps:
        name = app.get("name")
        if not isinstance(name, str) or not name:
            continue
        perm_messages[name] = fetch_permanent_messages_for_app(name)

    return perm_messages


def load_price_map():
    """
    Load price.json → { base_app_name: monthly_price_usd }
    """
    if not os.path.exists(PRICE_FILE):
        return {}

    try:
        with open(PRICE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return {}

    price_map = {}
    for k, v in raw.items():
        try:
            price_map[str(k)] = float(v)
        except Exception:
            continue
    return price_map


def fetch_fiat_wallet_txids():
    """
    Fetch all txids where the FIAT wallet participates.
    Used to classify a permanent-message payment as FIAT-sourced.
    """
    try:
        resp = requests.get(
            EXPLORER_TX_API_URL,
            params={"address": FIAT_WALLET_ADDRESS},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        txs = data.get("transactions", []) or []
        txids = {
            tx.get("txid")
            for tx in txs
            if isinstance(tx, dict) and tx.get("txid")
        }
        return txids
    except Exception:
        return set()


def update_cache():
    """Fetch fresh stats and write them into the cache file."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Updating cache...")

    try:
        apps = fetch_apps()
        nodes = fetch_nodes()
        locations = fetch_locations()

        # New: fetch permanent messages per app + price map + FIAT wallet txids
        perm_messages = load_permanent_messages_for_apps(apps)
        price_map = load_price_map()
        fiat_txids = fetch_fiat_wallet_txids()

        # Run main analytics from app.py
        from app import analyze_apps as full_analyzer

        stats = full_analyzer(
            apps,
            nodes,
            locations,
            perm_messages,
            price_map,
            fiat_txids,
        )

        # Add timestamp
        stats["last_updated"] = int(time.time() * 1000)

        # Write file
        with open(CACHE_FILE, "w") as f:
            json.dump(stats, f, indent=2)

        print(f"[OK] Cache updated → {CACHE_FILE}")

    except Exception as e:
        print(f"[ERROR] Failed to update cache: {e}")


if __name__ == "__main__":
    update_cache()
