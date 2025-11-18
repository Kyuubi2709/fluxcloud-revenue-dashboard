import os
import json
import time
import requests

from app import fetch_apps, fetch_nodes, fetch_locations

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "stats.json")
os.makedirs(CACHE_DIR, exist_ok=True)


def update_cache():
    print(f"[CACHE] Updating cache {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        apps = fetch_apps()
        nodes = fetch_nodes()
        locations = fetch_locations()

        from app import analyze_apps
        stats = analyze_apps(apps, nodes, locations)
        stats["last_updated"] = int(time.time() * 1000)

        with open(CACHE_FILE, "w") as f:
            json.dump(stats, f, indent=2)

        print("[CACHE] Updated OK")

    except Exception as e:
        print("[CACHE] ERROR:", e)


if __name__ == "__main__":
    update_cache()
