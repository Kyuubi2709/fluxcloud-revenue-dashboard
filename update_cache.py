import os
import json
import time
import traceback
from datetime import datetime

import requests
from app import fetch_apps, fetch_nodes, analyze_apps   # reuse your existing logic

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "stats.json")
TEMP_FILE = os.path.join(CACHE_DIR, "stats.tmp")


def log(msg):
    """Small logger with timestamps."""
    print(f"[{datetime.utcnow().isoformat()}] {msg}", flush=True)


def update_cache():
    """Fetch apps + nodes, analyze them, then write a fresh JSON cache."""
    try:
        log("Updating cache...")

        # Ensure cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)

        # Fetch data
        apps = fetch_apps()
        nodes = fetch_nodes()

        # Analyze
        data = analyze_apps(apps, nodes)

        # Write atomically: write → flush → replace
        with open(TEMP_FILE, "w") as f:
            json.dump(data, f, indent=2)

        os.replace(TEMP_FILE, CACHE_FILE)

        log("Cache update completed successfully.")
        return True

    except Exception as e:
        log(f"[ERROR] Failed to update cache: {e}")
        traceback.print_exc()

        # Cleanup temp file if it exists
        if os.path.exists(TEMP_FILE):
            try:
                os.remove(TEMP_FILE)
            except:
                pass

        return False


if __name__ == "__main__":
    update_cache()
