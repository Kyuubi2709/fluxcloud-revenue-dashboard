from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import requests
import re
import os
import threading
import time
import json
from collections import Counter

app = Flask(__name__, static_folder="static", template_folder="templates")

# Secret key for session
app.secret_key = "fluxcloud_dashboard_secret"

# Hardcoded login
LOGIN_USER = "fluxcloud"
LOGIN_PASS = "fluxcloud123"

# APIs
API_URL_APPS = "https://api.runonflux.io/apps/globalappsspecifications"
API_URL_NODES = "https://api.runonflux.io/daemon/viewdeterministicfluxnodelist"
API_URL_LOCATIONS = "https://api.runonflux.io/apps/locations"

# Marketplace app name pattern
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")

# Your company Flux address
TARGET_OWNER = "196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH"

# Tier hardware (per node)
TIER_HW = {
    "CUMULUS": {"cpu": 2, "ram_gb": 8, "hdd_gb": 220},
    "NIMBUS":  {"cpu": 4, "ram_gb": 32, "hdd_gb": 440},
    "STRATUS": {"cpu": 8, "ram_gb": 64, "hdd_gb": 880},
}

# Expire mapping
EXPIRE_BUCKETS = {
    22000:  "1w",
    44000:  "2w",
    88000:  "1m",
    264000: "3m",
    528000: "6m",
    1056000: "12m",
}

CACHE_FILE = "cache/stats.json"


# --------------------------- AUTH ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == LOGIN_USER and request.form.get("password") == LOGIN_PASS:
            session["logged_in"] = True
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid login")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ----------------------- Fetch helpers -----------------------
def fetch_apps():
    r = requests.get(API_URL_APPS, timeout=25)
    r.raise_for_status()
    return r.json().get("data", [])


def fetch_nodes():
    try:
        r = requests.get(API_URL_NODES, timeout=25)
        r.raise_for_status()
        return r.json().get("data", [])
    except:
        return []


def fetch_locations():
    try:
        r = requests.get(API_URL_LOCATIONS, timeout=25)
        r.raise_for_status()
        return r.json().get("data", [])
    except:
        return []


# ----------------------- Analytics -----------------------
def analyze_apps(apps, nodes, locations=None):
    apps = [a for a in apps if isinstance(a, dict)]
    total = len(apps)

    # ----- NEW Expire tracking -----
    expire_counter = {
        "1w": 0,
        "2w": 0,
        "1m": 0,
        "3m": 0,
        "6m": 0,
        "12m": 0,
        "other": 0,
    }

    for a in apps:
        exp = int(a.get("expire", 0))
        bucket = EXPIRE_BUCKETS.get(exp, "other")
        expire_counter[bucket] += 1

    # Compute percentages
    expire_distribution = {}
    for k, c in expire_counter.items():
        pct = round((c / total) * 100, 2) if total else 0
        expire_distribution[k] = {"count": c, "pct": pct}

    # Continue with existing logic, imported from previous version:
    from app_logic_main import run_full_analysis
    stats = run_full_analysis(apps, nodes, locations)

    # Attach new expire stats
    stats["expire_distribution"] = expire_distribution

    return stats


# --------------------- /stats endpoint ---------------------
@app.route("/stats")
def stats():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if not os.path.exists(CACHE_FILE):
        from update_cache import update_cache
        update_cache()

    try:
        with open(CACHE_FILE, "r") as f:
            return jsonify(json.load(f))
    except:
        return jsonify({"error": "Cache unavailable"}), 500


# --------------------- Manual refresh ----------------------
@app.route("/refresh", methods=["POST"])
def refresh():
    if not session.get("logged_in"):
        return jsonify({"status": "unauthorized"}), 403

    last_file = "cache/last_refresh.txt"
    now = time.time()
    cooldown = 900

    if os.path.exists(last_file):
        last = float(open(last_file).read().strip())
        if now - last < cooldown:
            return jsonify({"status": "cooldown"}), 429

    with open(last_file, "w") as f:
        f.write(str(now))

    def bg():
        from update_cache import update_cache
        update_cache()

    threading.Thread(target=bg).start()
    return jsonify({"status": "ok"})


# --------------------------- UI ---------------------------
@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
