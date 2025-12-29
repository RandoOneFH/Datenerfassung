from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ...classification.receipt_detector import detect_receipt
from ...engine import ReceiptEngine
from ...http_client import HttpRequestError, post_json
from ...models import CanonicalReceipt, IngestResult
from ...ocr.paddleocr_backend import OcrNotAvailableError, PaddleOcrConfig, ocr_image_path
from ...project_paths import ProjectPaths
from ...rules.loader import RuleSet
from ...storage import persist_canonical_receipt, slug, write_json


def _now(tz: str = "Europe/Berlin") -> datetime:
    try:
        zone = ZoneInfo(tz)
    except Exception:
        return datetime.now().astimezone()
    return datetime.now(tz=zone)


@dataclass(frozen=True, slots=True)
class IngestOrchestrator:
    paths: ProjectPaths
    ruleset: RuleSet
    receipt_engine: ReceiptEngine
    tz: str = "Europe/Berlin"

    @classmethod
    def detect(cls, *, tz: str = "Europe/Berlin") -> "IngestOrchestrator":
        paths = ProjectPaths.detect()
        paths.ensure_dirs()
        ruleset = RuleSet.load_from_dir(paths.rules_dir)
        receipt_engine = ReceiptEngine(ruleset, tz=tz)
        return cls(paths=paths, ruleset=ruleset, receipt_engine=receipt_engine, tz=tz)

    def ingest_text(self, text: str, *, source_name: str | None = None) -> IngestResult:
        ingest_event_id = str(uuid.uuid4())
        received_at = _now(self.tz).isoformat()

        raw_text_path = self.paths.raw_dir / "ocr_text" / f"{ingest_event_id}.txt"
        raw_text_path.write_text(text, encoding="utf-8")

        detection = detect_receipt(text, self.ruleset)

        receipt, canonical_path, route_info = self._route_or_fallback(
            text=text,
            ingest_event_id=ingest_event_id,
            source_type="text",
            detection=detection,
        )

        ingest_event_path = self.paths.raw_dir / "ingest_events" / f"{ingest_event_id}.json"
        write_json(
            ingest_event_path,
            {
                "ingest_event_id": ingest_event_id,
                "received_at": received_at,
                "source_type": "text",
                "source_name": source_name,
                "raw_text_path": self._rel(raw_text_path),
                "canonical_receipt_path": self._rel(canonical_path) if canonical_path else None,
                "detection": {
                    "is_receipt": detection.is_receipt,
                    "score": detection.score,
                    "reason": detection.reason,
                },
                **route_info,
            },
        )

        return IngestResult(
            ingest_event_id=ingest_event_id,
            status=route_info.get("status") or ("ok" if canonical_path else "stored_raw_text"),
            raw_text_path=self._rel(raw_text_path),
            ingest_event_path=self._rel(ingest_event_path),
            canonical_receipt_path=self._rel(canonical_path) if canonical_path else None,
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
        safe_stem = slug(original.stem or "image")
        suffix = original.suffix if original.suffix else ".jpg"
        raw_image_path = self.paths.raw_dir / "images" / f"{ingest_event_id}_{safe_stem}{suffix}"
        raw_image_path.write_bytes(image_bytes)

        ocr_engine = None
        if ocr_text is None:
            try:
                ocr_text, ocr_engine = self._run_ocr(raw_image_path)
            except OcrNotAvailableError as exc:
                ingest_event_path = self.paths.raw_dir / "ingest_events" / f"{ingest_event_id}.json"
                write_json(
                    ingest_event_path,
                    {
                        "ingest_event_id": ingest_event_id,
                        "received_at": received_at,
                        "source_type": "image",
                        "source_name": source_name,
                        "raw_image_path": self._rel(raw_image_path),
                        "status": "stored_raw_image",
                        "error": str(exc),
                    },
                )
                return IngestResult(
                    ingest_event_id=ingest_event_id,
                    status="stored_raw_image",
                    raw_image_path=self._rel(raw_image_path),
                    ingest_event_path=self._rel(ingest_event_path),
                )
            except RuntimeError as exc:
                ingest_event_path = self.paths.raw_dir / "ingest_events" / f"{ingest_event_id}.json"
                write_json(
                    ingest_event_path,
                    {
                        "ingest_event_id": ingest_event_id,
                        "received_at": received_at,
                        "source_type": "image",
                        "source_name": source_name,
                        "raw_image_path": self._rel(raw_image_path),
                        "status": "ocr_failed",
                        "error": str(exc),
                    },
                )
                return IngestResult(
                    ingest_event_id=ingest_event_id,
                    status="ocr_failed",
                    raw_image_path=self._rel(raw_image_path),
                    ingest_event_path=self._rel(ingest_event_path),
                )

        raw_text_path = self.paths.raw_dir / "ocr_text" / f"{ingest_event_id}.txt"
        raw_text_path.write_text(ocr_text, encoding="utf-8")

        detection = detect_receipt(ocr_text, self.ruleset)
        receipt, canonical_path, route_info = self._route_or_fallback(
            text=ocr_text,
            ingest_event_id=ingest_event_id,
            source_type="image",
            detection=detection,
        )

        ingest_event_path = self.paths.raw_dir / "ingest_events" / f"{ingest_event_id}.json"
        write_json(
            ingest_event_path,
            {
                "ingest_event_id": ingest_event_id,
                "received_at": received_at,
                "source_type": "image",
                "source_name": source_name,
                "raw_image_path": self._rel(raw_image_path),
                "raw_text_path": self._rel(raw_text_path),
                "canonical_receipt_path": self._rel(canonical_path) if canonical_path else None,
                "ocr": {"engine": ocr_engine, "provided": ocr_engine is None},
                "detection": {
                    "is_receipt": detection.is_receipt,
                    "score": detection.score,
                    "reason": detection.reason,
                },
                **route_info,
            },
        )

        return IngestResult(
            ingest_event_id=ingest_event_id,
            status=route_info.get("status") or ("ok" if canonical_path else "ocr_done"),
            raw_text_path=self._rel(raw_text_path),
            raw_image_path=self._rel(raw_image_path),
            ingest_event_path=self._rel(ingest_event_path),
            canonical_receipt_path=self._rel(canonical_path) if canonical_path else None,
            receipt=receipt,
        )

    def _run_ocr(self, image_path: Path) -> tuple[str, str]:
        cfg = PaddleOcrConfig(lang="german", use_angle_cls=True)
        text = ocr_image_path(image_path, config=cfg)
        return text, "paddleocr"

    def _route_or_fallback(
        self,
        *,
        text: str,
        ingest_event_id: str,
        source_type: str,
        detection,
    ) -> tuple[CanonicalReceipt | None, Path | None, dict]:
        if not detection.is_receipt:
            return None, None, {"status": "non_receipt"}

        receipt_service_url = os.getenv("HOUSEHOLD_RECEIPT_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
        allow_fallback = os.getenv("INGEST_LOCAL_FALLBACK", "1") not in {"0", "false", "False"}

        if receipt_service_url:
            try:
                result = post_json(
                    f"{receipt_service_url}/receipts/ingest_text",
                    {"text": text, "source_type": source_type, "ingest_event_id": ingest_event_id},
                    timeout_s=float(os.getenv("RECEIPT_SERVICE_TIMEOUT_S", "5")),
                )
                canonical_receipt_path = result.get("canonical_receipt_path")
                receipt = CanonicalReceipt.model_validate(result.get("receipt") or {})
                canonical_path = self._abs_from_rel(str(canonical_receipt_path))
                return receipt, canonical_path, {"status": "ok", "routed_to": receipt_service_url}
            except (HttpRequestError, Exception) as exc:
                if not allow_fallback:
                    return None, None, {"status": "route_failed", "route_error": str(exc)}

        receipt = self.receipt_engine.parse_text(text, source_type=source_type, ingest_event_id=ingest_event_id)
        canonical_path = persist_canonical_receipt(self.paths.canonical_dir, receipt)
        return receipt, canonical_path, {"status": "ok_local"}

    def _abs_from_rel(self, rel_or_abs: str) -> Path:
        p = Path(rel_or_abs)
        if p.is_absolute():
            return p
        return (self.paths.root / p).resolve()

    def _rel(self, path: Path | None) -> str:
        if path is None:
            return ""
        try:
            return path.relative_to(self.paths.root).as_posix()
        except Exception:
            return path.as_posix()
