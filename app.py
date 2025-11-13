from flask import Flask, jsonify, render_template
import requests
import re
from collections import Counter

app = Flask(__name__, static_folder="static", template_folder="templates")

API_URL = "https://api.runonflux.io/apps/globalappsspecifications"
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")

def fetch_apps():
    resp = requests.get(API_URL, timeout=20)
    resp.raise_for_status()
    return resp.json()

def analyze_apps(apps):
    total = len(apps)
    marketplace = []
    custom = []

    for app_info in apps:
        name = app_info.get("name", "")
        if TIMESTAMP_REGEX.search(name):
            marketplace.append(name)
        else:
            custom.append(name)

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
