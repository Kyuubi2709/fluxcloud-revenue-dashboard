"""Helpers for loading account metadata from CSV."""

from __future__ import annotations

import csv
import os
from typing import Set, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ACCOUNTS_CSV = os.path.join(BASE_DIR, "accounts.csv")


def load_accounts_from_csv(csv_path: str = ACCOUNTS_CSV) -> Tuple[Set[str], Set[str]]:
    """
    Read accounts.csv and return:
    - all_sso_flux_ids: set of all btcn_public values (non-NULL, non-empty)
    - appleid_flux_ids: subset of btcn_public where email is an AppleID relay
      (ends with '@privaterelay.appleid.com')
    """
    all_sso_flux_ids: Set[str] = set()
    appleid_flux_ids: Set[str] = set()

    if not os.path.exists(csv_path):
        return all_sso_flux_ids, appleid_flux_ids

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = (row.get("email") or "").strip().strip('"')
                btcn = (row.get("btcn_public") or "").strip().strip('"')

                # Normalise NULL values
                if email.upper() == "NULL":
                    email = ""
                if btcn.upper() == "NULL":
                    btcn = ""

                if not email and not btcn:
                    continue

                if btcn:
                    all_sso_flux_ids.add(btcn)

                    if email.endswith("@privaterelay.appleid.com"):
                        appleid_flux_ids.add(btcn)
    except Exception:
        # Fail quietly; metrics will just be zero
        return set(), set()

    return all_sso_flux_ids, appleid_flux_ids
