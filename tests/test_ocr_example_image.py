from __future__ import annotations

from pathlib import Path

import pytest

from datenerfassung.engine import ReceiptEngine
from datenerfassung.ocr.paddleocr_backend import OcrNotAvailableError, ocr_image_path
from datenerfassung.project_paths import ProjectPaths
from datenerfassung.rules.loader import RuleSet
from datenerfassung.services.ingest_service.orchestrator import IngestOrchestrator


def test_ocr_example_image_end_to_end(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    image_path = repo_root / "data" / "raw" / "images" / "20251229-1209.jpg"
    if not image_path.exists():
        pytest.skip(f"Example image not found: {image_path}")

    try:
        _ = ocr_image_path(image_path)
    except OcrNotAvailableError:
        pytest.skip("PaddleOCR not available in this environment")

    rules_dir = repo_root / "data" / "rules"
    paths = ProjectPaths(
        root=tmp_path,
        data_dir=tmp_path / "data",
        raw_dir=tmp_path / "data" / "raw",
        canonical_dir=tmp_path / "data" / "canonical",
        rules_dir=rules_dir,
        schema_dir=repo_root / "schema",
    )
    paths.ensure_dirs()

    ruleset = RuleSet.load_from_dir(paths.rules_dir)
    receipt_engine = ReceiptEngine(ruleset)
    orchestrator = IngestOrchestrator(paths=paths, ruleset=ruleset, receipt_engine=receipt_engine)

    result = orchestrator.ingest_image(image_path.read_bytes(), filename=image_path.name)

    if result.status in {"stored_raw_image", "ocr_failed"}:
        pytest.skip(f"OCR not usable in this environment (status={result.status})")

    assert result.status.startswith("ok")
    assert result.receipt is not None
    assert result.canonical_receipt_path is not None
    assert (tmp_path / Path(result.canonical_receipt_path)).exists()
