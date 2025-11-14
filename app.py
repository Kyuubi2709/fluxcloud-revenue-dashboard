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

API_URL_APPS = "https://api.runonflux.io/apps/globalappsspecifications"
API_URL_NODES = "https://api.runonflux.io/daemon/viewdeterministiczelnodes"

TIMESTAMP_REGEX = re.compile(r"\d{10,}$")

# your company Flux address
TARGET_OWNER = "196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH"

# Tier hardware (per node) – based on your specs
TIER_HW = {
    "CUMULUS": {"cpu": 2, "ram_gb": 8, "hdd_gb": 220},
    "NIMBUS":  {"cpu": 4, "ram_gb": 32, "hdd_gb": 440},
    "STRATUS": {"cpu": 8, "ram_gb": 64, "hdd_gb": 880},
}


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
# FETCHERS
# ---------------------------
def fetch_apps():
    resp = requests.get(API_URL_APPS, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", [])


def fetch_nodes():
    """
    Fetch deterministic Flux nodes to know how many Cumulus/Nimbus/Stratus
    we have and to map node IP -> tier.
    """
    try:
        resp = requests.get(API_URL_NODES, timeout=20)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:
        # If node API fails for some reason, just return empty list
        return []


# ---------------------------
# ANALYTICS ENGINE
# ---------------------------
def analyze_apps(apps, nodes):

    apps = [a for a in apps if isinstance(a, dict)]
    nodes = [n for n in nodes if isinstance(n, dict)]

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

    # total resource usage (apps)
    total_cpu = 0.0       # vCPU
    total_ram_mb = 0.0    # MB
    total_hdd_gb = 0.0    # GB

    # ---- Tier-related structures ----
    # Node IP -> tier
    node_tier_map = {}
    # Capacity: how many nodes, total resources per tier
    tier_capacity = {
        tier: {"nodes": 0, "cpu": 0.0, "ram_gb": 0.0, "hdd_gb": 0.0}
        for tier in TIER_HW
    }
    # Usage: how much app resource runs on each tier
    tier_usage = {
        tier: {"instances": 0, "cpu": 0.0, "ram_gb": 0.0, "hdd_gb": 0.0}
        for tier in TIER_HW
    }

    # -----------------------------
    # Build node_tier_map & capacity from nodes API
    # -----------------------------
    for node in nodes:
        ip = node.get("ip") or node.get("ipaddress") or ""
        raw_tier = node.get("tier") or ""
        if not ip or not raw_tier:
            continue

        ip_only = ip.split(":")[0] if isinstance(ip, str) else ip
        tier = str(raw_tier).upper()

        if tier in TIER_HW and ip_only:
            node_tier_map[ip_only] = tier
            tier_capacity[tier]["nodes"] += 1

    # Compute per-tier capacity + network totals
    network_total_cpu = 0.0
    network_total_ram_gb = 0.0
    network_total_hdd_gb = 0.0

    for tier, hw in TIER_HW.items():
        count = tier_capacity[tier]["nodes"]
        tier_capacity[tier]["cpu"] = hw["cpu"] * count
        tier_capacity[tier]["ram_gb"] = hw["ram_gb"] * count
        tier_capacity[tier]["hdd_gb"] = hw["hdd_gb"] * count

        network_total_cpu += tier_capacity[tier]["cpu"]
        network_total_ram_gb += tier_capacity[tier]["ram_gb"]
        network_total_hdd_gb += tier_capacity[tier]["hdd_gb"]

    # -----------------------------
    # Process each app
    # -----------------------------
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
        cpu_per_inst = 0.0
        ram_per_inst_mb = 0.0
        hdd_per_inst_gb = 0.0
        used_compose = False

        if isinstance(compose, list) and len(compose) > 0:
            for comp in compose:
                if isinstance(comp, dict):
                    used_compose = True
                    cpu_per_inst += float(comp.get("cpu", 0) or 0)
                    ram_per_inst_mb += float(comp.get("ram", 0) or 0)   # MB
                    hdd_per_inst_gb += float(comp.get("hdd", 0) or 0)   # GB

        if not used_compose:
            # fall back to top-level cpu/ram/hdd
            cpu_per_inst = float(app_info.get("cpu", 0) or 0)
            ram_per_inst_mb = float(app_info.get("ram", 0) or 0)
            hdd_per_inst_gb = float(app_info.get("hdd", 0) or 0)

        # Multiply by instances for total app usage
        total_cpu += cpu_per_inst * instances
        total_ram_mb += ram_per_inst_mb * instances
        total_hdd_gb += hdd_per_inst_gb * instances

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
        # PER-TIER USAGE (by node IP)
        # -----------------------------
        nodes_list = app_info.get("nodes", [])
        if isinstance(nodes_list, list) and nodes_list:
            ram_inst_gb = ram_per_inst_mb / 1024.0 if ram_per_inst_mb else 0.0
            for node_ip in nodes_list:
                if not isinstance(node_ip, str):
                    continue
                ip_only = node_ip.split(":")[0]
                tier = node_tier_map.get(ip_only)
                if not tier or tier not in tier_usage:
                    continue

                tier_usage[tier]["instances"] += 1
                tier_usage[tier]["cpu"] += cpu_per_inst
                tier_usage[tier]["ram_gb"] += ram_inst_gb
                tier_usage[tier]["hdd_gb"] += hdd_per_inst_gb

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
    # Resource conversions (apps)
    # -----------------------------
    total_ram_gb = total_ram_mb / 1024 if total_ram_mb else 0

    # network totals in TB only (as requested)
    network_total_ram_tb = (network_total_ram_gb / 1000) if network_total_ram_gb else 0
    network_total_hdd_tb = (network_total_hdd_gb / 1000) if network_total_hdd_gb else 0

    # -----------------------------
    # Utilization %
    # -----------------------------
    cpu_util_pct = round((total_cpu / network_total_cpu) * 100, 2) if network_total_cpu else 0
    ram_util_pct = round((total_ram_gb / network_total_ram_gb) * 100, 2) if network_total_ram_gb else 0
    hdd_util_pct = round((total_hdd_gb / network_total_hdd_gb) * 100, 2) if network_total_hdd_gb else 0

    # Prepare tier_usage & tier_capacity for output
    tier_usage_out = {}
    for tier in TIER_HW:
        u = tier_usage[tier]
        tier_usage_out[tier] = {
            "instances": u["instances"],
            "cpu": round(u["cpu"], 2),
            "ram_gb": round(u["ram_gb"], 2),
            "hdd_gb": round(u["hdd_gb"], 2),
        }

    tier_capacity_out = {}
    for tier in TIER_HW:
        c = tier_capacity[tier]
        tier_capacity_out[tier] = {
            "nodes": c["nodes"],
            "cpu": c["cpu"],
            "ram_tb": round((c["ram_gb"] / 1000) if c["ram_gb"] else 0, 2),
            "hdd_tb": round((c["hdd_gb"] / 1000) if c["hdd_gb"] else 0, 2),
        }

    return {
        # basic totals
        "total_apps": total,
        "marketplace_apps": len(marketplace),
        "custom_apps": len(custom),

        # owners
        "unique_owners": len(unique_owners),

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

        # secret / static ip
        "total_with_secrets": total_with_secrets,
        "total_with_staticip": total_with_staticip,
        "marketplace_with_secrets": marketplace_with_secrets,
        "marketplace_with_staticip": marketplace_with_staticip,

        # app resource usage (primary: GB)
        "total_cpu": round(total_cpu, 2),
        "total_ram_gb": round(total_ram_gb, 2),
        "total_hdd_gb": round(total_hdd_gb, 2),

        # tier usage
        "tier_usage": tier_usage_out,

        # network capacity (TB only for RAM/HDD)
        "network_total_cpu": network_total_cpu,
        "network_total_ram_tb": round(network_total_ram_tb, 2),
        "network_total_hdd_tb": round(network_total_hdd_tb, 2),

        # tier capacity
        "tier_capacity": tier_capacity_out,

        # utilization
        "cpu_util_pct": cpu_util_pct,
        "ram_util_pct": ram_util_pct,
        "hdd_util_pct": hdd_util_pct,

        # top marketplace apps
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
    apps = fetch_apps()
    nodes = fetch_nodes()
    return jsonify(analyze_apps(apps, nodes))


@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
