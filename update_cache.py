import os
import json
import time
import requests
from analyze_fluxcloud import analyze_apps, API_URL as APPS_API_URL

NODES_API_URL = "https://api.runonflux.io/daemon/viewdeterministicfluxnodelist"

CACHE_DIR = "/app/cache"
CACHE_FILE = os.path.join(CACHE_DIR, "stats.json")

os.makedirs(CACHE_DIR, exist_ok=True)


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


def main():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Updating cache...")

    try:
        apps = fetch_apps()
        nodes = fetch_nodes()

        # Run main analytics
        from app import analyze_apps as full_analyzer
        stats = full_analyzer(apps, nodes)

        # Add timestamp
        stats["last_updated"] = int(time.time() * 1000)

        # Write file
        with open(CACHE_FILE, "w") as f:
            json.dump(stats, f, indent=2)

        print(f"[OK] Cache updated → {CACHE_FILE}")

    except Exception as e:
        print(f"[ERROR] Failed to update cache: {e}")


if __name__ == "__main__":
    main()
