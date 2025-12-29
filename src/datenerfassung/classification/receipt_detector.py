from __future__ import annotations

import re
from dataclasses import dataclass

from ..rules.loader import RuleSet
from ..rules.merchants import detect_merchant
from ..rules.normalization import clean_text


@dataclass(frozen=True, slots=True)
class ReceiptDetection:
    is_receipt: bool
    score: float
    reason: str


_PRICE = re.compile(r"\b\d+[.,]\d{2}\b")
_PERCENT = re.compile(r"\b\d{1,2}\s*%")


def detect_receipt(text: str, ruleset: RuleSet) -> ReceiptDetection:
    cleaned = clean_text(text)
    if not cleaned:
        return ReceiptDetection(is_receipt=False, score=0.0, reason="empty_text")

    merchant = detect_merchant(text, ruleset.merchants)
    if merchant:
        return ReceiptDetection(is_receipt=True, score=0.95, reason=f"merchant:{merchant.id}")

    hints = 0
    for token in [
        "summe",
        "gesamt",
        "mwst",
        "ust",
        "kasse",
        "bon",
        "kartenzahlung",
        "wechselgeld",
        "pfand",
        "ec",
        "karte",
        "visa",
        "mastercard",
    ]:
        if token in cleaned:
            hints += 1

    prices = len(_PRICE.findall(text))
    percents = len(_PERCENT.findall(text))
    non_empty_lines = sum(1 for ln in text.splitlines() if ln.strip())
    line_score = min(0.2, 0.2 * (non_empty_lines / 40.0))  # saturates at ~40 lines

    score = min(1.0, 0.15 * hints + 0.03 * prices + 0.05 * min(percents, 4) + line_score)

    reason = f"hints={hints},prices={prices},percents={percents},lines={non_empty_lines}"
    if score >= 0.45:
        return ReceiptDetection(is_receipt=True, score=score, reason=reason)
    return ReceiptDetection(is_receipt=False, score=score, reason=reason)
