"""Helpers for loading pricing configuration."""

from __future__ import annotations

import json
import os
import re
from typing import Dict

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PRICE_JSON = os.path.join(BASE_DIR, "price.json")


def load_price_config(price_path: str = PRICE_JSON) -> Dict[str, float]:
    """
    Load price.json which maps base marketplace app names (no timestamp)
    to USD price per month.

      {
        "KaspaNode16GB": 27.2,
        "KaspaNode24GB": 31.2,
        ...
      }

    We also strip C-style /* ... */ and // comments if present.
    """
    if not os.path.exists(price_path):
        return {}

    try:
        with open(price_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Strip /* ... */ comments
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        # Strip // comments to end of line
        text = re.sub(r"//.*", "", text)

        data = json.loads(text)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}
