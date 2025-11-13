from flask import Flask, jsonify, render_template
import requests
import re
from collections import Counter

app = Flask(__name__, static_folder="static", template_folder="templates")

API_URL = "https://api.runonflux.io/apps/globalappsspecifications"
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")


def fetch_apps():
    try:
        resp = requests.get(API_URL, timeout=20)
        resp.raise_for_status()

        data = resp.json()

        # Expected API format:
        # { "status": "...", "data": [ {app}, {app}, ... ] }
        if isinstance(data, dict) and "data" in data:
            apps = data["data"]
        elif isinstance(data, list):
            # fallback: unexpected but safe
            apps = data
        else:
            print("Unexpected API structure:", type(data), data)
            return []

        # Ensure we only keep dict items
        apps = [a for a in apps if isinstance(a, dict)]
        return apps

    except Exception as e:
        print("FETCH ERROR:", e)
        return []


def analyze_apps(apps):
    # Ensure only dict objects
    apps = [a for a in apps if isinstance(a, dict)]

    total = len(apps)
    marketplace = []
    custom = []

    for app_info in apps:
        name = app_info.get("name", "")

        if TIMESTAMP_REGEX.search(name):  # Marketplace app
            marketplace.append(name)
        else:  # Custom app
            custom.append(name)

    # Strip timestamps for grouping marketplace deployments
    base_names = [TIMESTAMP_REGEX.sub("", name) for name in marketplace]
    counts = Counter(base_names)
    top5 = counts.most_common(5)

    return {
        "total_apps": total,
        "marketplace_apps": len(marketplace),
        "custom_apps": len(custom),
        "top_marketplace_apps": [
            {"name": n, "deployments": c} for n, c in top5
        ],
    }


@app.route("/stats")
def stats():
    apps = fetch_apps()
    return jsonify(analyze_apps(apps))


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
