from __future__ import annotations

import re
import unicodedata

from .loader import NormalizationRules


_NON_ALNUM = re.compile(r"[^0-9a-zA-Z]+")
_WS = re.compile(r"\s+")


def clean_text(value: str) -> str:
    value = value.casefold()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = _NON_ALNUM.sub(" ", value)
    value = _WS.sub(" ", value).strip()
    return value


def tokenize(clean_value: str) -> list[str]:
    if not clean_value:
        return []
    return [t for t in clean_value.split(" ") if t]


def normalize_name(name_raw: str, rules: NormalizationRules) -> tuple[str, list[str], str]:
    name_clean = clean_text(name_raw)
    name_clean = _apply_synonyms(name_clean, rules)
    tokens = tokenize(name_clean)

    tokens = [t for t in tokens if t not in rules.stopwords]

    name_norm = "_".join(tokens) if tokens else ""
    return name_clean, tokens, name_norm


def _apply_synonyms(name_clean: str, rules: NormalizationRules) -> str:
    out = name_clean
    for raw_key, raw_value in rules.synonyms.items():
        key = clean_text(raw_key)
        value = clean_text(raw_value)
        if not key or not value:
            continue
        key_parts = [re.escape(p) for p in key.split(" ") if p]
        if not key_parts:
            continue
        sep = r"\s+"
        pattern = rf"\b{sep.join(key_parts)}\b"
        out = re.sub(pattern, value, out)
    out = _WS.sub(" ", out).strip()
    return out
