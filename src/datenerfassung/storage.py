from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import CanonicalReceipt


def slug(value: str) -> str:
    out = []
    for ch in value.casefold():
        if ch.isalnum():
            out.append(ch)
        else:
            out.append("_")
    slug_value = "".join(out)
    while "__" in slug_value:
        slug_value = slug_value.replace("__", "_")
    return slug_value.strip("_") or "unknown"


def canonical_receipt_path(canonical_dir: Path, receipt: CanonicalReceipt) -> Path:
    dt = datetime.fromisoformat(receipt.receipt.datetime)
    year = dt.year
    date_prefix = dt.date().isoformat()
    merchant_name = receipt.receipt.merchant.name or receipt.receipt.merchant.id or "unknown"
    stem = f"{date_prefix}_{slug(merchant_name)}_{receipt.receipt.id}"
    return canonical_dir / "receipts" / str(year) / f"{stem}.json"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def persist_canonical_receipt(canonical_dir: Path, receipt: CanonicalReceipt) -> Path:
    path = canonical_receipt_path(canonical_dir, receipt)
    write_json(path, receipt.model_dump(mode="json"))
    return path

