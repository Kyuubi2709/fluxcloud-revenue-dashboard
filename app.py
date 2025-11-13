from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import requests
import re
from collections import Counter

app = Flask(__name__, static_folder="static", template_folder="templates")

# Secret key for session cookies
app.secret_key = "fluxcloud_dashboard_secret"

# Hardcoded login creds
LOGIN_USER = "fluxcloud"
LOGIN_PASS = "fluxcloud123"

API_URL = "https://api.runonflux.io/apps/globalappsspecifications"
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")
TARGET_OWNER = "196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH"   # your company address


# ---------------------------
# AUTHENTICATION
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")

        if user == LOGIN_USER and pw == LOGIN_PASS:
            session["logged_in"] = True
            return redirect(url_for("home"))

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------
# Fetch API
# ---------------------------
def fetch_apps():
    resp = requests.get(API_URL, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", [])


# ---------------------------
# ANALYTICS FUNCTION
# ---------------------------
def analyze_apps(apps):
    apps = [a for a in apps if isinstance(a, dict)]

    total = len(apps)
    marketplace = []
    custom = []

    total_instances = 0
    company_deployments = 0
    company_instances = 0

    # CONTACT METRICS
    total_with_contacts = 0
    marketplace_with_contacts = 0
    custom_with_contacts = 0

    # FLAG METRICS
    total_with_secrets = 0
    total_with_staticip = 0
    marketplace_with_secrets = 0
    marketplace_with_staticip = 0

    for app_info in apps:
        name = app_info.get("name", "")
        owner = app_info.get("owner", "")
        instances = int(app_info.get("instances", 0))

        contacts = app_info.get("contacts", [])
        secrets = app_info.get("secrets", "")
        staticip = app_info.get("staticip", False)

        total_instances += instances

        # company stats
        if owner == TARGET_OWNER:
            company_deployments += 1
            company_instances += instances

        # ----- CONTACT USAGE -----
        if isinstance(contacts, list) and len(contacts) > 0:
            total_with_contacts += 1

        # ----- SECRET DETECTION (fixed) -----
        has_secrets = isinstance(secrets, str) and secrets.strip() != ""

        if has_secrets:
            total_with_secrets += 1

        # ----- STATIC IP -----
        if bool(staticip) is True:
            total_with_staticip += 1

        # ----- MARKETPLACE OR CUSTOM -----
        is_marketplace = bool(TIMESTAMP_REGEX.search(name))

        if is_marketplace:
            marketplace.append(name)

            if isinstance(contacts, list) and len(contacts) > 0:
                marketplace_with_contacts += 1

            if has_secrets:
                marketplace_with_secrets += 1

            if bool(staticip) is True:
                marketplace_with_staticip += 1

        else:
            custom.append(name)

            if isinstance(contacts, list) and len(contacts) > 0:
                custom_with_contacts += 1

    # group marketplace templates (top 5)
    base_names = [TIMESTAMP_REGEX.sub("", name) for name in marketplace]
    counts = Counter(base_names)
    top5 = counts.most_common(5)

    # Percentages
    marketplace_pct = round((len(marketplace) / total) * 100, 2) if total else 0.0
    custom_pct = round((len(custom) / total) * 100, 2) if total else 0.0

    marketplace_contact_pct = round((marketplace_with_contacts / len(marketplace)) * 100, 2) if len(marketplace) else 0.0
    custom_contact_pct = round((custom_with_contacts / len(custom)) * 100, 2) if len(custom) else 0.0
    total_contact_pct = round((total_with_contacts / total) * 100, 2) if total else 0.0

    return {
        "total_apps": total,
        "marketplace_apps": len(marketplace),
        "custom_apps": len(custom),

        # percentages
        "marketplace_pct": marketplace_pct,
        "custom_pct": custom_pct,

        # instances
        "total_instances": total_instances,
        "company_deployments": company_deployments,
        "company_instances": company_instances,

        # contact metrics
        "total_with_contacts": total_with_contacts,
        "total_contact_pct": total_contact_pct,
        "marketplace_with_contacts": marketplace_with_contacts,
        "marketplace_contact_pct": marketplace_contact_pct,
        "custom_with_contacts": custom_with_contacts,
        "custom_contact_pct": custom_contact_pct,

        # flag metrics
        "total_with_secrets": total_with_secrets,
        "total_with_staticip": total_with_staticip,
        "marketplace_with_secrets": marketplace_with_secrets,
        "marketplace_with_staticip": marketplace_with_staticip,

        # top marketplace templates
        "top_marketplace_apps": [
            {"name": n, "deployments": c}
            for n, c in top5
        ],
    }


# ---------------------------
# WEB ROUTES
# ---------------------------
@app.route("/stats")
def stats():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    apps = fetch_apps()
    return jsonify(analyze_apps(apps))


@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")


# ---------------------------
# RUN APP
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
