import os
import json
import time
import re

from analytics.engine import analyze_apps
from services.flux_api import (
    fetch_apps,
    fetch_locations,
    fetch_nodes,
    fetch_permanent_messages,
)

# Paths
CACHE_DIR = "/app/cache"
CACHE_FILE = os.path.join(CACHE_DIR, "stats.json")
PERM_MSG_DIR = os.path.join(CACHE_DIR, "permanent_messages")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(PERM_MSG_DIR, exist_ok=True)


def safe_filename(name: str) -> str:
    """Make app name safe as a filename."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def fetch_permanent_messages_for_app(app_name: str):
    """
    Fetch permanent messages for a single app and cache them under
    /app/cache/permanent_messages/<SAFE_APPNAME>.json
    """
    path = os.path.join(PERM_MSG_DIR, f"{safe_filename(app_name)}.json")

    data = fetch_permanent_messages(app_name)
    if not data and os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
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


def update_cache():
    """Fetch fresh stats and write them into the cache file."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Updating cache...")

    try:
        apps = fetch_apps()
        nodes = fetch_nodes()
        locations = fetch_locations()

        perm_messages = load_permanent_messages_for_apps(apps)

        stats = analyze_apps(
            apps,
            nodes,
            locations,
            perm_messages,
            None,   # accounts_csv_path (unused)
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
