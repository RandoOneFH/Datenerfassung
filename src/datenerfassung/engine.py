from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import (
    CanonicalReceipt,
    IngestResult,
    LineItem,
    LineItemClassification,
    Provenance,
    ReceiptInfo,
    ReceiptMerchant,
    Totals,
)
from .project_paths import ProjectPaths
from .receipt.parser_de_v1 import parse_receipt_text
from .receipt.structured_receipt_v1 import StructuredReceiptV1
from .rules.categorization import categorize
from .rules.loader import RuleSet
from .rules.merchants import detect_merchant
from .rules.normalization import normalize_name
from .storage import canonical_receipt_path, persist_canonical_receipt, slug, write_json


def _now(tz: str = "Europe/Berlin") -> datetime:
    try:
        zone = ZoneInfo(tz)
    except Exception:
        return datetime.now().astimezone()
    return datetime.now(tz=zone)


def _slug(value: str) -> str:
    return slug(value)


@dataclass(frozen=True, slots=True)
class ReceiptEngine:
    ruleset: RuleSet
    tz: str = "Europe/Berlin"

    def parse_text(self, text: str, *, source_type: str, ingest_event_id: str | None = None) -> CanonicalReceipt:
        parsed = parse_receipt_text(text, tz=self.tz)
        merchant = detect_merchant(text, self.ruleset.merchants)

        receipt_id = str(uuid.uuid4())
        dt = parsed.datetime_hint or _now(self.tz)

        line_items: list[LineItem] = []
        for parsed_line in parsed.lines:
            line_id = str(uuid.uuid4())
            name_clean, tokens, name_norm = normalize_name(
                parsed_line.name_raw, self.ruleset.normalization
            )
            category, rule_id, confidence, tags_add = categorize(
                name_clean, tokens, self.ruleset.categories
            )

            item = LineItem(
                line_id=line_id,
                name_raw=parsed_line.name_raw,
                name_clean=name_clean,
                tokens=tokens,
                name_norm=name_norm,
                quantity=parsed_line.quantity,
                unit_price=parsed_line.unit_price,
                total=parsed_line.total,
                category=category,
                tags=tags_add,
                classification=LineItemClassification(rule_id=rule_id, confidence=confidence),
            )
            line_items.append(item)

        total = _sum_totals(line_items)

        receipt = CanonicalReceipt(
            receipt=ReceiptInfo(
                id=receipt_id,
                merchant=ReceiptMerchant(
                    id=merchant.id if merchant else None,
                    name=(merchant.names[0] if merchant and merchant.names else parsed.merchant_name_hint),
                ),
                datetime=dt.isoformat(),
            ),
            line_items=line_items,
            totals=Totals(total=total),
            provenance=Provenance(
                source_type=source_type,
                ocr_engine=None,
                parser="de_receipt_v1",
                created_at=_now(self.tz).isoformat(),
                ingest_event_id=ingest_event_id,
            ),
        )
        return receipt


def _sum_totals(line_items: list[LineItem]) -> float | None:
    totals = [li.total for li in line_items if li.total is not None]
    if not totals:
        return None
    return round(sum(totals), 2)


class IngestEngine:
    def __init__(self, paths: ProjectPaths | None = None, *, tz: str = "Europe/Berlin") -> None:
        self.paths = paths or ProjectPaths.detect()
        self.paths.ensure_dirs()
        self.tz = tz
        self.ruleset = RuleSet.load_from_dir(self.paths.rules_dir)
        self.receipt_engine = ReceiptEngine(self.ruleset, tz=tz)

    def ingest_text(self, text: str, *, source_name: str | None = None) -> IngestResult:
        ingest_event_id = str(uuid.uuid4())
        received_at = _now(self.tz).isoformat()

        raw_text_path = self.paths.raw_dir / "ocr_text" / f"{ingest_event_id}.txt"
        raw_text_path.write_text(text, encoding="utf-8")

        receipt = self.receipt_engine.parse_text(
            text, source_type="text", ingest_event_id=ingest_event_id
        )

        canonical_path = persist_canonical_receipt(self.paths.canonical_dir, receipt)

        ingest_event_path = self.paths.raw_dir / "ingest_events" / f"{ingest_event_id}.json"
        write_json(
            ingest_event_path,
            {
                "ingest_event_id": ingest_event_id,
                "received_at": received_at,
                "source_type": "text",
                "source_name": source_name,
                "raw_text_path": self._rel(raw_text_path),
                "canonical_receipt_path": self._rel(canonical_path),
            },
        )

        return IngestResult(
            ingest_event_id=ingest_event_id,
            status="ok",
            raw_text_path=self._rel(raw_text_path),
            ingest_event_path=self._rel(ingest_event_path),
            canonical_receipt_path=self._rel(canonical_path),
            receipt=receipt,
        )

    def ingest_receipt_json(self, payload: dict, *, source_name: str | None = None) -> IngestResult:
        ingest_event_id = str(uuid.uuid4())
        received_at = _now(self.tz).isoformat()

        raw_json_path = self.paths.raw_dir / "ocr_text" / f"{ingest_event_id}.json"
        write_json(raw_json_path, payload)

        structured = StructuredReceiptV1.model_validate(payload)
        receipt = self._canonical_from_structured(structured, ingest_event_id=ingest_event_id)

        canonical_path = persist_canonical_receipt(self.paths.canonical_dir, receipt)

        ingest_event_path = self.paths.raw_dir / "ingest_events" / f"{ingest_event_id}.json"
        write_json(
            ingest_event_path,
            {
                "ingest_event_id": ingest_event_id,
                "received_at": received_at,
                "source_type": "receipt_json",
                "source_name": source_name,
                "raw_receipt_json_path": self._rel(raw_json_path),
                "canonical_receipt_path": self._rel(canonical_path),
                "structured_confidence": structured.confidence,
            },
        )

        return IngestResult(
            ingest_event_id=ingest_event_id,
            status="ok",
            raw_receipt_json_path=self._rel(raw_json_path),
            ingest_event_path=self._rel(ingest_event_path),
            canonical_receipt_path=self._rel(canonical_path),
            receipt=receipt,
        )

    def ingest_image(
        self,
        image_bytes: bytes,
        *,
        filename: str | None = None,
        ocr_text: str | None = None,
        source_name: str | None = None,
    ) -> IngestResult:
        ingest_event_id = str(uuid.uuid4())
        received_at = _now(self.tz).isoformat()

        original = Path(filename or "image.jpg")
        safe_stem = _slug(original.stem or "image")
        suffix = original.suffix if original.suffix else ".jpg"
        raw_image_path = self.paths.raw_dir / "images" / f"{ingest_event_id}_{safe_stem}{suffix}"
        raw_image_path.write_bytes(image_bytes)

        receipt = None
        canonical_path = None
        status = "stored_raw_image"

        raw_text_path = None
        if ocr_text is not None:
            raw_text_path = self.paths.raw_dir / "ocr_text" / f"{ingest_event_id}.txt"
            raw_text_path.write_text(ocr_text, encoding="utf-8")
            receipt = self.receipt_engine.parse_text(
                ocr_text, source_type="image", ingest_event_id=ingest_event_id
            )
            canonical_path = persist_canonical_receipt(self.paths.canonical_dir, receipt)
            status = "ok"

        ingest_event_path = self.paths.raw_dir / "ingest_events" / f"{ingest_event_id}.json"
        write_json(
            ingest_event_path,
            {
                "ingest_event_id": ingest_event_id,
                "received_at": received_at,
                "source_type": "image",
                "source_name": source_name,
                "raw_image_path": self._rel(raw_image_path),
                "raw_text_path": self._rel(raw_text_path) if raw_text_path else None,
                "canonical_receipt_path": self._rel(canonical_path) if canonical_path else None,
                "note": None if receipt else "Provide ocr_text to process (OCR integration is not wired yet).",
            },
        )

        return IngestResult(
            ingest_event_id=ingest_event_id,
            status=status,
            raw_text_path=self._rel(raw_text_path) if raw_text_path else None,
            raw_image_path=self._rel(raw_image_path),
            ingest_event_path=self._rel(ingest_event_path),
            canonical_receipt_path=self._rel(canonical_path) if canonical_path else None,
            receipt=receipt,
        )

    def _canonical_from_structured(
        self, structured: StructuredReceiptV1, *, ingest_event_id: str
    ) -> CanonicalReceipt:
        receipt_id = str(uuid.uuid4())
        dt = structured.datetime or _now(self.tz).isoformat()

        merchant_id = None
        merchant_name = structured.merchant.name
        if merchant_name:
            merchant = detect_merchant(merchant_name, self.ruleset.merchants)
            merchant_id = merchant.id if merchant else None

        line_items: list[LineItem] = []
        for it in structured.items:
            line_id = str(uuid.uuid4())
            name_clean, tokens, name_norm = normalize_name(it.name, self.ruleset.normalization)
            category, rule_id, confidence, tags_add = categorize(
                name_clean, tokens, self.ruleset.categories
            )
            line_items.append(
                LineItem(
                    line_id=line_id,
                    name_raw=it.name,
                    name_clean=name_clean,
                    tokens=tokens,
                    name_norm=name_norm,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    total=it.total,
                    vat_rate=it.vat_rate,
                    category=category,
                    tags=tags_add,
                    classification=LineItemClassification(rule_id=rule_id, confidence=confidence),
                )
            )

        total = structured.totals.total if structured.totals.total is not None else _sum_totals(line_items)
        vat_breakdown = []
        for vat in structured.totals.vat:
            if vat.gross is None:
                continue
            vat_breakdown.append({"rate": vat.rate, "gross": vat.gross})

        return CanonicalReceipt(
            receipt=ReceiptInfo(
                id=receipt_id,
                merchant=ReceiptMerchant(
                    id=merchant_id,
                    name=merchant_name,
                    store_id=structured.merchant.store_id,
                ),
                datetime=dt,
                currency=structured.currency or "EUR",
                payment_method=structured.totals.payment_method,
            ),
            line_items=line_items,
            totals=Totals(total=total, vat_breakdown=vat_breakdown),
            provenance=Provenance(
                source_type="receipt_json",
                ocr_engine=None,
                parser="structured_receipt_v1",
                created_at=_now(self.tz).isoformat(),
                ingest_event_id=ingest_event_id,
            ),
        )

    def _canonical_receipt_path(self, receipt: CanonicalReceipt) -> Path:
        return canonical_receipt_path(self.paths.canonical_dir, receipt)

    def _rel(self, path: Path | None) -> str:
        if path is None:
            return ""
        try:
            return path.relative_to(self.paths.root).as_posix()
        except Exception:
            return path.as_posix()


def _write_json(path: Path, data: object) -> None:
    write_json(path, data)
