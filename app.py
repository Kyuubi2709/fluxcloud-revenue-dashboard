from flask import Flask, jsonify, render_template, request, redirect, url_for, session
import requests
import re
from collections import Counter

app = Flask(__name__, static_folder="static", template_folder="templates")

# Secret key for session
app.secret_key = "fluxcloud_dashboard_secret"

# Hardcoded login
LOGIN_USER = "fluxcloud"
LOGIN_PASS = "fluxcloud123"

API_URL = "https://api.runonflux.io/apps/globalappsspecifications"
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")

# your company Flux address
TARGET_OWNER = "196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH"


# ---------------------------
# AUTH
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

    apps = [a for a in apps if isinstance(a, dict)]

    total = len(apps)
    marketplace = []
    custom = []

    total_instances = 0
    company_deployments = 0
    company_instances = 0

    # Contact / secret / staticIP
    total_with_contacts = 0
    marketplace_with_contacts = 0
    custom_with_contacts = 0

    total_with_secrets = 0
    total_with_staticip = 0
    marketplace_with_secrets = 0
    marketplace_with_staticip = 0

    # unique owners
    unique_owners = set()

    # total resource usage
    total_cpu = 0.0       # vCPU
    total_ram_mb = 0.0    # MB
    total_hdd_gb = 0.0    # GB

    for app_info in apps:

        name = app_info.get("name", "")
        owner = app_info.get("owner", "")
        instances = int(app_info.get("instances", 0))

        # Track owners
        if owner:
            unique_owners.add(owner)

        # -----------------------------
        # RESOURCE EXTRACTION (multi-container aware)
        # -----------------------------
        compose = app_info.get("compose", [])
        cpu_app = 0.0
        ram_app = 0.0
        hdd_app = 0.0
        used_compose = False

        if isinstance(compose, list) and len(compose) > 0:
            for comp in compose:
                if isinstance(comp, dict):
                    used_compose = True
                    cpu_app += float(comp.get("cpu", 0) or 0)
                    ram_app += float(comp.get("ram", 0) or 0)   # MB
                    hdd_app += float(comp.get("hdd", 0) or 0)   # GB

        if not used_compose:
            # fall back to top-level cpu/ram/hdd
            cpu_app = float(app_info.get("cpu", 0) or 0)
            ram_app = float(app_info.get("ram", 0) or 0)
            hdd_app = float(app_info.get("hdd", 0) or 0)

        # multiply by instances
        total_cpu += cpu_app * instances
        total_ram_mb += ram_app * instances
        total_hdd_gb += hdd_app * instances

        total_instances += instances

        # -----------------------------
        # COMPANY STATS
        # -----------------------------
        if owner == TARGET_OWNER:
            company_deployments += 1
            company_instances += instances

        # -----------------------------
        # CONTACTS
        # -----------------------------
        contacts = app_info.get("contacts", [])
        has_contacts = isinstance(contacts, list) and len(contacts) > 0

        if has_contacts:
            total_with_contacts += 1

        # -----------------------------
        # SECRETS detection
        # -----------------------------
        secrets = app_info.get("secrets", "")

        if not secrets and isinstance(compose, list) and len(compose) > 0 and isinstance(compose[0], dict):
            secrets = compose[0].get("secrets", "")

        has_secrets = isinstance(secrets, str) and secrets.strip() != ""

        # STATIC IP (app-level only)
        staticip = bool(app_info.get("staticip", False))

        if has_secrets:
            total_with_secrets += 1
        if staticip:
            total_with_staticip += 1

        # -----------------------------
        # MARKETPLACE VS CUSTOM
        # -----------------------------
        is_marketplace = bool(TIMESTAMP_REGEX.search(name))

        if is_marketplace:

            marketplace.append(name)

            if has_contacts:
                marketplace_with_contacts += 1
            if has_secrets:
                marketplace_with_secrets += 1
            if staticip:
                marketplace_with_staticip += 1

        else:
            custom.append(name)

            if has_contacts:
                custom_with_contacts += 1

    # -----------------------------
    # TOP 5 MARKETPLACE APPS
    # -----------------------------
    base_names = [TIMESTAMP_REGEX.sub("", name) for name in marketplace]
    counts = Counter(base_names)
    top5 = counts.most_common(5)

    # -----------------------------
    # Percentages
    # -----------------------------
    marketplace_pct = round((len(marketplace) / total) * 100, 2) if total else 0
    custom_pct = round((len(custom) / total) * 100, 2) if total else 0

    total_contact_pct = round((total_with_contacts / total) * 100, 2) if total else 0
    marketplace_contact_pct = round((marketplace_with_contacts / len(marketplace)) * 100, 2) if len(marketplace) else 0
    custom_contact_pct = round((custom_with_contacts / len(custom)) * 100, 2) if len(custom) else 0

    # -----------------------------
    # Resource conversions
    # -----------------------------
    # MB -> GB (binary-ish)
    total_ram_gb = total_ram_mb / 1024 if total_ram_mb else 0
    # HDD already in GB
    # TB we don't really need in backend for display, but keep for completeness (decimal-based)
    total_ram_tb = total_ram_gb / 1000 if total_ram_gb else 0
    total_hdd_tb = total_hdd_gb / 1000 if total_hdd_gb else 0

    return {
        "total_apps": total,
        "marketplace_apps": len(marketplace),
        "custom_apps": len(custom),

        # Owners
        "unique_owners": len(unique_owners),

        # Percentages
        "marketplace_pct": marketplace_pct,
        "custom_pct": custom_pct,

        # Instances + company
        "total_instances": total_instances,
        "company_deployments": company_deployments,
        "company_instances": company_instances,

        # Contacts
        "total_with_contacts": total_with_contacts,
        "total_contact_pct": total_contact_pct,
        "marketplace_with_contacts": marketplace_with_contacts,
        "marketplace_contact_pct": marketplace_contact_pct,
        "custom_with_contacts": custom_with_contacts,
        "custom_contact_pct": custom_contact_pct,

        # Flags
        "total_with_secrets": total_with_secrets,
        "total_with_staticip": total_with_staticip,
        "marketplace_with_secrets": marketplace_with_secrets,
        "marketplace_with_staticip": marketplace_with_staticip,

        # Resource usage (primary: GB)
        "total_cpu": round(total_cpu, 2),
        "total_ram_gb": round(total_ram_gb, 2),
        "total_hdd_gb": round(total_hdd_gb, 2),

        # Secondary TB values (not used in UI, but kept)
        "total_ram_tb": round(total_ram_tb, 4),
        "total_hdd_tb": round(total_hdd_tb, 4),

        # Top marketplace
        "top_marketplace_apps": [
            {"name": n, "deployments": c} for n, c in top5
        ],
    }


# ---------------------------
# ROUTES
# ---------------------------
@app.route("/stats")
def stats():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return jsonify(analyze_apps(fetch_apps()))


@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
