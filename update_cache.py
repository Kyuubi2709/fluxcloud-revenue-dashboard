import json
import time
from app import fetch_apps, fetch_nodes, analyze_apps

CACHE_FILE = "cache/stats.json"


def update_cache():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Updating cache...")

    try:
        apps = fetch_apps()
        nodes = fetch_nodes()

        stats = analyze_apps(apps, nodes)

        with open(CACHE_FILE, "w") as f:
            json.dump(stats, f)

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Cache updated successfully.")

    except Exception as e:
        print(f"[ERROR] Failed to update cache: {e}")


if __name__ == "__main__":
    update_cache()
