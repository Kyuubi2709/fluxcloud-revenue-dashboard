"""API client helpers for Flux endpoints."""

from __future__ import annotations

import requests

# APIs
API_URL_APPS = "https://api.runonflux.io/apps/globalappsspecifications"
API_URL_NODES = "https://api.runonflux.io/daemon/viewdeterministicfluxnodelist"
API_URL_LOCATIONS = "https://api.runonflux.io/apps/locations"
PERM_MSG_API_URL = "https://api.runonflux.io/apps/permanentmessages"
EXPLORER_TX_API_URL = "https://api.runonflux.io/explorer/transactions"


def fetch_apps():
    resp = requests.get(API_URL_APPS, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", [])


def fetch_nodes():
    try:
        resp = requests.get(API_URL_NODES, timeout=20)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:
        return []


def fetch_locations():
    try:
        resp = requests.get(API_URL_LOCATIONS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except Exception:
        return []


def fetch_permanent_messages(app_name: str):
    params = {"appname": app_name}
    try:
        resp = requests.get(PERM_MSG_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:
        return []


def fetch_fiat_wallet_transactions(address: str):
    try:
        resp = requests.get(EXPLORER_TX_API_URL, params={"address": address}, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        txs = data.get("transactions", []) or []
        return {tx.get("txid") for tx in txs if isinstance(tx, dict) and tx.get("txid")}
    except Exception:
        return set()
