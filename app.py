from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import requests
import re
from collections import Counter

app = Flask(__name__, static_folder="static", template_folder="templates")

# SECRET KEY for sessions
app.secret_key = "supersecretkey_fluxcloud_dashboard_123"

# Hardcoded credentials
VALID_USERNAME = "fluxcloud"
VALID_PASSWORD = "fluxcloud123"

API_URL = "https://api.runonflux.io/apps/globalappsspecifications"
TARGET_OWNER = "196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH"
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")


### -------------------------
### LOGIN REQUIRED WRAPPER
### -------------------------
def login_required(route_function):
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return route_function(*args, **kwargs)
    wrapper.__name__ = route_function.__name__
    return wrapper


### -------------------------
### FETCHING APPS
### -------------------------
def fetch_apps():
    try:
        resp = requests.get(API_URL, timeout=20)
        resp.raise_for_status()

        data = resp.json()

        if isinstance(data, dict) and "data" in data:
            apps = data["data"]
        elif isinstance(data, list):
            apps = data
        else:
            return []

        return [a for a in apps if isinstance(a, dict)]

    except Exception as e:
        print("FETCH ERROR:", e)
        return []


### -------------------------
### ANALYZE APPS
### -------------------------
def analyze_apps(apps):
    apps = [a for a in apps if isinstance(a, dict)]

    total = len(apps)
    marketplace = []
    custom = []

    total_instances = 0
    company_deployments = 0
    company_instances = 0

    marketplace_with_contacts = 0

    for app_info in apps:
        name = app_info.get("name", "")
        owner = app_info.get("owner", "")
        instances = int(app_info.get("instances", 0))
        contacts = app_info.get("contacts", [])

        total_instances += instances

        if owner == TARGET_OWNER:
            company_deployments += 1
            company_instances += instances

        if TIMESTAMP_REGEX.search(name):
            marketplace.append(name)

            # count marketplace deployments with contacts
            if isinstance(contacts, list) and len(contacts) > 0:
                marketplace_with_contacts += 1

        else:
            custom.append(name)

    # Group marketplace base names for the top 5
    base_names = [TIMESTAMP_REGEX.sub("", name) for name in marketplace]
    counts = Counter(base_names)
    top5 = counts.most_common(5)

    if total > 0:
        marketplace_pct = round((len(marketplace) / total) * 100, 2)
        custom_pct = round((len(custom) / total) * 100, 2)
    else:
        marketplace_pct = custom_pct = 0.0

    if len(marketplace) > 0:
        marketplace_contact_pct = round((marketplace_with_contacts / len(marketplace)) * 100, 2)
    else:
        marketplace_contact_pct = 0.0

    return {
        "total_apps": total,
        "marketplace_apps": len(marketplace),
        "custom_apps": len(custom),
        "marketplace_pct": marketplace_pct,
        "custom_pct": custom_pct,
        "total_instances": total_instances,
        "company_deployments": company_deployments,
        "company_instances": company_instances,
        "marketplace_with_contacts": marketplace_with_contacts,
        "marketplace_contact_pct": marketplace_contact_pct,
        "top_marketplace_apps": [
            {"name": n, "deployments": c} for n, c in top5
        ],
    }


### -------------------------
### ROUTES
### -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")

        if user == VALID_USERNAME and pw == VALID_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    return render_template("index.html")


@app.route("/stats")
@login_required
def stats():
    apps = fetch_apps()
    return jsonify(analyze_apps(apps))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
