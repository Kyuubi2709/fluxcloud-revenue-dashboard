from flask import Flask, jsonify, render_template
import requests
import re
from collections import Counter

app = Flask(__name__, static_folder="static", template_folder="templates")

API_URL = "https://api.runonflux.io/apps/globalappsspecifications"
TARGET_OWNER = "196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH"
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")


def fetch_apps():
    try:
        resp = requests.get(API_URL, timeout=20)
        resp.raise_for_status()

        data = resp.json()

        # Extract real app list from API
        if isinstance(data, dict) and "data" in data:
            apps = data["data"]
        elif isinstance(data, list):
            apps = data
        else:
            print("Unexpected API structure:", type(data), data)
            return []

        # Ensure only dictionaries
        apps = [a for a in apps if isinstance(a, dict)]
        return apps

    except Exception as e:
        print("FETCH ERROR:", e)
        return []


def analyze_apps(apps):
    # Make sure only dicts are used
    apps = [a for a in apps if isinstance(a, dict)]

    total = len(apps)
    marketplace = []
    custom = []

    total_instances = 0
    company_deployments = 0
    company_instances = 0

    for app_info in apps:
        name = app_info.get("name", "")
        owner = app_info.get("owner", "")
        instances = int(app_info.get("instances", 0))

        # Count total instances
        total_instances += instances

        # Count company-owned deployments + instances
        if owner == TARGET_OWNER:
            company_deployments += 1
            company_instances += instances

        # Marketplace detection
        if TIMESTAMP_REGEX.search(name):
            marketplace.append(name)
        else:
            custom.append(name)

    # Marketplace grouping for top 5 apps
    base_names = [TIMESTAMP_REGEX.sub("", name) for name in marketplace]
    counts = Counter(base_names)
    top5 = counts.most_common(5)

    # Percentage breakdown
    if total > 0:
        marketplace_pct = round((len(marketplace) / total) * 100, 2)
        custom_pct = round((len(custom) / total) * 100, 2)
    else:
        marketplace_pct = custom_pct = 0.0

    return {
        "total_apps": total,
        "marketplace_apps": len(marketplace),
        "custom_apps": len(custom),
        "marketplace_pct": marketplace_pct,
        "custom_pct": custom_pct,
        "total_instances": total_instances,
        "company_deployments": company_deployments,
        "company_instances": company_instances,
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
