from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import requests
import re
from collections import Counter

app = Flask(__name__, static_folder="static", template_folder="templates")

# Secret key for login session
app.secret_key = "fluxcloud_dashboard_secret"

# Hardcoded login
LOGIN_USER = "fluxcloud"
LOGIN_PASS = "fluxcloud123"

API_URL = "https://api.runonflux.io/apps/globalappsspecifications"
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")

# your company Flux address
TARGET_OWNER = "196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH"


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
# FETCH APPS
# ---------------------------
def fetch_apps():
    resp = requests.get(API_URL, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", [])


# ---------------------------
# ANALYTICS ENGINE
# ---------------------------
def analyze_apps(apps):

    # ensure only dictionaries
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

    # SECRET / STATICIP METRICS
    total_with_secrets = 0
    total_with_staticip = 0
    marketplace_with_secrets = 0
    marketplace_with_staticip = 0

    for app_info in apps:

        name = app_info.get("name", "")
        owner = app_info.get("owner", "")
        instances = int(app_info.get("instances", 0))
        contacts = app_info.get("contacts", [])
        staticip = app_info.get("staticip", False)

        # FIX: Extract secrets correctly
        secrets = app_info.get("secrets", "")

        # sometimes secrets live inside compose[0]
        if not secrets:
            compose = app_info.get("compose", [])
            if isinstance(compose, list) and len(compose) > 0:
                first_block = compose[0]
                if isinstance(first_block, dict):
                    secrets = first_block.get("secrets", "")

        # A secret exists if it's a non-empty string
        has_secrets = isinstance(secrets, str) and secrets.strip() != ""

        # instance counting
        total_instances += instances

        # company specific stats
        if owner == TARGET_OWNER:
            company_deployments += 1
            company_instances += instances

        # contact metrics
        has_contacts = isinstance(contacts, list) and len(contacts) > 0
        if has_contacts:
            total_with_contacts += 1

        # global secret/staticip metrics
        if has_secrets:
            total_with_secrets += 1

        if bool(staticip) is True:
            total_with_staticip += 1

        # determine marketplace app
        is_marketplace = bool(TIMESTAMP_REGEX.search(name))

        if is_marketplace:
            marketplace.append(name)

            if has_contacts:
                marketplace_with_contacts += 1
            if has_secrets:
                marketplace_with_secrets += 1
            if bool(staticip) is True:
                marketplace_with_staticip += 1

        else:
            custom.append(name)
            if has_contacts:
                custom_with_contacts += 1

    # top marketplace templates (group by prefix)
    base_names = [TIMESTAMP_REGEX.sub("", name) for name in marketplace]
    counts = Counter(base_names)
    top5 = counts.most_common(5)

    # Percentages
    marketplace_pct = round((len(marketplace) / total) * 100, 2) if total else 0.0
    custom_pct = round((len(custom) / total) * 100, 2) if total else 0.0

    # Contact percentages
    total_contact_pct = round((total_with_contacts / total) * 100, 2) if total else 0.0
    marketplace_contact_pct = round((marketplace_with_contacts / len(marketplace)) * 100, 2) if len(marketplace) else 0.0
    custom_contact_pct = round((custom_with_contacts / len(custom)) * 100, 2) if len(custom) else 0.0

    return {
        # totals
        "total_apps": total,
        "marketplace_apps": len(marketplace),
        "custom_apps": len(custom),

        # percentages
        "marketplace_pct": marketplace_pct,
        "custom_pct": custom_pct,

        # instances + company stats
        "total_instances": total_instances,
        "company_deployments": company_deployments,
        "company_instances": company_instances,

        # contact stats
        "total_with_contacts": total_with_contacts,
        "total_contact_pct": total_contact_pct,
        "marketplace_with_contacts": marketplace_with_contacts,
        "marketplace_contact_pct": marketplace_contact_pct,
        "custom_with_contacts": custom_with_contacts,
        "custom_contact_pct": custom_contact_pct,

        # secret & staticIP
        "total_with_secrets": total_with_secrets,
        "total_with_staticip": total_with_staticip,
        "marketplace_with_secrets": marketplace_with_secrets,
        "marketplace_with_staticip": marketplace_with_staticip,

        # top marketplace apps
        "top_marketplace_apps": [
            {"name": n, "deployments": c}
            for n, c in top5
        ],
    }


# ---------------------------
# ROUTES
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
# RUN SERVER
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
