from __future__ import annotations

from .loader import Merchant, MerchantsRules
from .normalization import clean_text


def detect_merchant(text: str, rules: MerchantsRules) -> Merchant | None:
    haystack = clean_text(text)
    for merchant in rules.merchants:
        for name in merchant.names:
            if clean_text(name) and clean_text(name) in haystack:
                return merchant
    return None

