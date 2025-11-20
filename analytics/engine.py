"""Analytics engine for Flux app statistics and revenue calculations."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, Optional, Set

from data.accounts import load_accounts_from_csv
from data.pricing import load_price_config

# Marketplace app name pattern (timestamp suffix)
TIMESTAMP_REGEX = re.compile(r"\d{10,}$")

# Your company Flux address
TARGET_OWNER = "196GJWyLxzAw3MirTT7Bqs2iGpUQio29GH"

# Tier hardware (per node)
TIER_HW = {
    "CUMULUS": {"cpu": 2, "ram_gb": 8, "hdd_gb": 220},
    "NIMBUS": {"cpu": 4, "ram_gb": 32, "hdd_gb": 440},
    "STRATUS": {"cpu": 8, "ram_gb": 64, "hdd_gb": 880},
}

# Approx blocks per month (30s block time, 30 days)
BLOCKS_PER_MONTH = 86400

# Address used when company deploys on behalf of users (FIAT payments)
FIAT_DEPLOYER_ADDRESSES: Set[str] = {
    "t1XktDZ9Z1QiefMYE5nMFohe8VG2c2BD5A5",
}


def analyze_apps(
    apps: Iterable[Dict],
    nodes: Iterable[Dict],
    locations: Optional[Iterable[Dict]] = None,
    permanent_messages: Optional[Dict] = None,
    accounts_csv_path: Optional[str] = None,
) -> Dict:
    apps = [a for a in apps if isinstance(a, dict)]
    nodes = [n for n in nodes if isinstance(n, dict)]
    locations = [l for l in (locations or []) if isinstance(l, dict)]

    total = len(apps)
    marketplace = []
    custom = []

    total_instances = 0
    company_deployments = 0
    company_instances = 0

    total_with_contacts = 0
    marketplace_with_contacts = 0
    custom_with_contacts = 0

    total_with_secrets = 0
    total_with_staticip = 0
    marketplace_with_secrets = 0
    marketplace_with_staticip = 0

    unique_owners: Set[str] = set()

    total_cpu = 0.0
    total_ram_mb = 0.0
    total_hdd_gb = 0.0

    # Node tier map and capacity
    node_tier_map: Dict[str, str] = {}
    tier_capacity: Dict[str, Dict[str, float]] = {
        tier: {"nodes": 0, "cpu": 0, "ram_gb": 0, "hdd_gb": 0} for tier in TIER_HW
    }

    # Build node tier mapping
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

    app_resource_map: Dict[str, Dict[str, float]] = {}

    # ----------------------------------------------------------------------
    # PROCESS APPS: stats + build resource map
    # ----------------------------------------------------------------------
    for app_info in apps:
        name = app_info.get("name", "")
        owner = app_info.get("owner", "")
        instances = int(app_info.get("instances", 0))

        if owner:
            unique_owners.add(owner)

        compose = app_info.get("compose", [])
        cpu_per_inst = 0.0
        ram_mb = 0.0
        hdd_gb = 0.0

        used_compose = False
        if isinstance(compose, list) and compose:
            for comp in compose:
                if isinstance(comp, dict):
                    used_compose = True
                    cpu_per_inst += float(comp.get("cpu", 0) or 0)
                    ram_mb += float(comp.get("ram", 0) or 0)
                    hdd_gb += float(comp.get("hdd", 0) or 0)

        if not used_compose:
            cpu_per_inst = float(app_info.get("cpu", 0) or 0)
            ram_mb = float(app_info.get("ram", 0) or 0)
            hdd_gb = float(app_info.get("hdd", 0) or 0)

        if name:
            app_resource_map[name] = {"cpu": cpu_per_inst, "ram_mb": ram_mb, "hdd_gb": hdd_gb}

        total_cpu += cpu_per_inst * instances
        total_ram_mb += ram_mb * instances
        total_hdd_gb += hdd_gb * instances
        total_instances += instances

        if owner == TARGET_OWNER:
            company_deployments += 1
            company_instances += instances

        contacts = app_info.get("contacts", [])
        has_contacts = isinstance(contacts, list) and len(contacts) > 0

        if has_contacts:
            total_with_contacts += 1

        secrets = app_info.get("secrets", "")
        if not secrets and compose and isinstance(compose[0], dict):
            secrets = compose[0].get("secrets", "")

        has_secrets = isinstance(secrets, str) and secrets.strip() != ""
        staticip = bool(app_info.get("staticip", False))

        if has_secrets:
            total_with_secrets += 1
        if staticip:
            total_with_staticip += 1

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

    # Top marketplace grouped
    base_names = [TIMESTAMP_REGEX.sub("", n) for n in marketplace]
    top5 = Counter(base_names).most_common(5)

    marketplace_pct = round((len(marketplace) / total) * 100, 2) if total else 0
    custom_pct = round((len(custom) / total) * 100, 2) if total else 0

    total_contact_pct = round((total_with_contacts / total) * 100, 2) if total else 0
    marketplace_contact_pct = round((marketplace_with_contacts / len(marketplace)) * 100, 2) if marketplace else 0
    custom_contact_pct = round((custom_with_contacts / len(custom)) * 100, 2) if custom else 0

    total_ram_gb = total_ram_mb / 1024 if total_ram_mb else 0
    network_total_ram_tb = (network_total_ram_gb / 1000) if network_total_ram_gb else 0
    network_total_hdd_tb = (network_total_hdd_gb / 1000) if network_total_hdd_gb else 0

    cpu_util_pct = round((total_cpu / network_total_cpu) * 100, 2) if network_total_cpu else 0
    ram_util_pct = round((total_ram_gb / network_total_ram_gb) * 100, 2) if network_total_ram_gb else 0
    hdd_util_pct = round((total_hdd_gb / network_total_hdd_gb) * 100, 2) if network_total_hdd_gb else 0

    tier_capacity_out = {}
    for tier in TIER_HW:
        c = tier_capacity[tier]
        tier_capacity_out[tier] = {
            "nodes": c["nodes"],
            "cpu": c["cpu"],
            "ram_tb": round((c["ram_gb"] / 1000) if c["ram_gb"] else 0, 2),
            "hdd_tb": round((c["hdd_gb"] / 1000) if c["hdd_gb"] else 0, 2),
        }

    # =====================================================================
    # REAL USAGE via locations
    # =====================================================================
    resources_total_cpu_used = 0.0
    resources_total_ram_mb_used = 0.0
    resources_total_hdd_gb_used = 0.0

    resources_tier_usage: Dict[str, Dict[str, float]] = {t: {"instances": 0, "cpu": 0, "ram_gb": 0, "hdd_gb": 0} for t in TIER_HW}
    resources_tier_usage["UNKNOWN"] = {"instances": 0, "cpu": 0, "ram_gb": 0, "hdd_gb": 0}

    # Track nodes running at least one instance
    used_nodes: Dict[str, Set[str]] = {tier: set() for tier in TIER_HW}

    for loc in locations:
        app_name = loc.get("name") or loc.get("app") or ""
        if not app_name:
            continue

        res = app_resource_map.get(app_name, None)
        cpu = float(res["cpu"]) if res else 0.0
        ram_mb = float(res["ram_mb"]) if res else 0.0
        hdd_gb = float(res["hdd_gb"]) if res else 0.0

        ip_raw = loc.get("ip", "")
        ip_only = ip_raw.split(":")[0] if isinstance(ip_raw, str) else ip_raw
        tier = node_tier_map.get(ip_only)

        bucket = tier if tier in TIER_HW else "UNKNOWN"

        resources_tier_usage[bucket]["instances"] += 1
        resources_tier_usage[bucket]["cpu"] += cpu
        resources_tier_usage[bucket]["ram_gb"] += ram_mb / 1024 if ram_mb else 0
        resources_tier_usage[bucket]["hdd_gb"] += hdd_gb

        resources_total_cpu_used += cpu
        resources_total_ram_mb_used += ram_mb
        resources_total_hdd_gb_used += hdd_gb

        if tier in used_nodes:
            used_nodes[tier].add(ip_only)

    resources_total_ram_gb_used = (
        resources_total_ram_mb_used / 1024 if resources_total_ram_mb_used else 0
    )

    resources_cpu_util_pct = round((resources_total_cpu_used / network_total_cpu) * 100, 2) if network_total_cpu else 0
    resources_ram_util_pct = round((resources_total_ram_gb_used / network_total_ram_gb) * 100, 2) if network_total_ram_gb else 0
    resources_hdd_util_pct = round((resources_total_hdd_gb_used / network_total_hdd_gb) * 100, 2) if network_total_hdd_gb else 0

    resources_tier_usage_out = {
        tier: {
            "instances": u["instances"],
            "cpu": round(u["cpu"], 2),
            "ram_gb": round(u["ram_gb"], 2),
            "hdd_gb": round(u["hdd_gb"], 2),
        }
        for tier, u in resources_tier_usage.items()
    }

    # NEW: per-tier utilization (real usage)
    tier_utilization = {}
    for tier in TIER_HW:
        cap = tier_capacity[tier]
        u = resources_tier_usage.get(tier, {"cpu": 0, "ram_gb": 0, "hdd_gb": 0})

        tier_utilization[tier] = {
            "cpu_util_pct": round((u["cpu"] / cap["cpu"]) * 100, 2) if cap["cpu"] else 0,
            "ram_util_pct": round((u["ram_gb"] / cap["ram_gb"]) * 100, 2) if cap["ram_gb"] else 0,
            "hdd_util_pct": round((u["hdd_gb"] / cap["hdd_gb"]) * 100, 2) if cap["hdd_gb"] else 0,
        }

    # TIER NODE UTILIZATION (for pie chart)
    tier_node_usage = {}
    for tier in TIER_HW:
        used = len(used_nodes[tier])
        total_nodes = tier_capacity[tier]["nodes"]
        pct = round((used / total_nodes) * 100, 2) if total_nodes else 0

        tier_node_usage[tier] = {
            "used_nodes": used,
            "total_nodes": total_nodes,
            "pct": pct
        }

    # NEW: SSO + AppleID metrics from accounts.csv
    all_sso_flux_ids, appleid_flux_ids = load_accounts_from_csv(accounts_csv_path) if accounts_csv_path else load_accounts_from_csv()
    flux_app_owners = unique_owners  # set of all owners of at least one app

    sso_owner_ids = flux_app_owners.intersection(all_sso_flux_ids)
    appleid_owner_ids = flux_app_owners.intersection(appleid_flux_ids)

    sso_owners = len(sso_owner_ids)
    appleid_app_owners = len(appleid_owner_ids)

    # NEW: REVENUE METRICS (USD, based on price.json + expire)
    price_cfg = load_price_config()

    total_revenue_usd = 0.0
    flux_revenue_usd = 0.0
    fiat_revenue_usd = 0.0
    marketplace_revenue_usd = 0.0
    custom_revenue_usd = 0.0

    revenue_by_owner: Dict[str, float] = defaultdict(float)

    for app_info in apps:
        name = app_info.get("name", "")
        owner = app_info.get("owner", "") or ""
        expire_blocks = app_info.get("expire", 0)

        # Normalize expire to int
        try:
            expire_blocks = int(expire_blocks or 0)
        except Exception:
            expire_blocks = 0

        # Only priced apps contribute to revenue
        base_name = TIMESTAMP_REGEX.sub("", name)
        price_month = price_cfg.get(base_name)

        if not price_month:
            continue  # no price defined yet

        # Approx months purchased from expire
        months = (expire_blocks / BLOCKS_PER_MONTH) if expire_blocks > 0 else 0.0
        if months <= 0:
            continue

        try:
            price_month = float(price_month)
        except Exception:
            continue

        revenue_usd = price_month * months

        total_revenue_usd += revenue_usd
        revenue_by_owner[owner] += revenue_usd

        is_marketplace = bool(TIMESTAMP_REGEX.search(name))
        if is_marketplace:
            marketplace_revenue_usd += revenue_usd
        else:
            custom_revenue_usd += revenue_usd

        if owner in FIAT_DEPLOYER_ADDRESSES:
            fiat_revenue_usd += revenue_usd
        else:
            flux_revenue_usd += revenue_usd

    # Top 5 paying owners by USD
    top_paying_owners = []
    for owner, amt in sorted(revenue_by_owner.items(), key=lambda x: x[1], reverse=True)[:5]:
        top_paying_owners.append({
            "owner": owner,
            "revenue_usd": round(amt, 2),
        })

    return {
        "total_apps": total,
        "marketplace_apps": len(marketplace),
        "custom_apps": len(custom),
        "unique_owners": len(unique_owners),

        "marketplace_pct": marketplace_pct,
        "custom_pct": custom_pct,

        "total_instances": total_instances,
        "company_deployments": company_deployments,
        "company_instances": company_instances,

        "total_with_contacts": total_with_contacts,
        "total_contact_pct": total_contact_pct,
        "marketplace_with_contacts": marketplace_with_contacts,
        "marketplace_contact_pct": marketplace_contact_pct,
        "custom_with_contacts": custom_with_contacts,
        "custom_contact_pct": custom_contact_pct,

        "total_with_secrets": total_with_secrets,
        "total_with_staticip": total_with_staticip,
        "marketplace_with_secrets": marketplace_with_secrets,
        "marketplace_with_staticip": marketplace_with_staticip,

        # NEW owner auth metrics
        "sso_owners": sso_owners,
        "appleid_app_owners": appleid_app_owners,

        "total_cpu": round(total_cpu, 2),
        "total_ram_gb": round(total_ram_gb, 2),
        "total_hdd_gb": round(total_hdd_gb, 2),

        "network_total_cpu": network_total_cpu,
        "network_total_ram_tb": round(network_total_ram_tb, 2),
        "network_total_hdd_tb": round(network_total_hdd_tb, 2),
        "tier_capacity": tier_capacity_out,

        "cpu_util_pct": cpu_util_pct,
        "ram_util_pct": ram_util_pct,
        "hdd_util_pct": hdd_util_pct,

        "resources_total_cpu_used": round(resources_total_cpu_used, 2),
        "resources_total_ram_gb_used": round(resources_total_ram_gb_used, 2),
        "resources_total_hdd_gb_used": round(resources_total_hdd_gb_used, 2),
        "resources_cpu_util_pct": resources_cpu_util_pct,
        "resources_ram_util_pct": resources_ram_util_pct,
        "resources_hdd_util_pct": resources_hdd_util_pct,
        "resources_tier_usage": resources_tier_usage_out,

        "tier_utilization": tier_utilization,
        "tier_node_usage": tier_node_usage,

        "top_marketplace_apps": [
            {"name": n, "deployments": c} for n, c in top5
        ],

        # NEW revenue metrics (USD)
        "total_revenue_usd": round(total_revenue_usd, 2),
        "flux_revenue_usd": round(flux_revenue_usd, 2),
        "fiat_revenue_usd": round(fiat_revenue_usd, 2),
        "marketplace_revenue_usd": round(marketplace_revenue_usd, 2),
        "custom_revenue_usd": round(custom_revenue_usd, 2),
        "top_paying_owners": top_paying_owners,
    }
