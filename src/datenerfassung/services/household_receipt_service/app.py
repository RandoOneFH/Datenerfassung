from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ...models import CanonicalReceipt
from ...project_paths import ProjectPaths
from ...rules.loader import RuleSet
from ...engine import ReceiptEngine
from ...storage import persist_canonical_receipt


class ParseTextRequest(BaseModel):
    text: str = Field(min_length=1)
    ingest_event_id: str | None = None
    source_type: str = "text"


class ReceiptIngestResponse(BaseModel):
    canonical_receipt_path: str
    receipt: CanonicalReceipt


app = FastAPI(title="Datenerfassung Household Receipt Service", version="0.1.0")
paths = ProjectPaths.detect()
ruleset = RuleSet.load_from_dir(paths.rules_dir)
engine = ReceiptEngine(ruleset)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/receipts/parse_text", response_model=CanonicalReceipt)
def parse_text(req: ParseTextRequest) -> CanonicalReceipt:
    return engine.parse_text(req.text, source_type=req.source_type, ingest_event_id=req.ingest_event_id)


@app.post("/receipts/ingest_text", response_model=ReceiptIngestResponse)
def ingest_text(req: ParseTextRequest) -> ReceiptIngestResponse:
    receipt = engine.parse_text(req.text, source_type=req.source_type, ingest_event_id=req.ingest_event_id)
    canonical_path = persist_canonical_receipt(paths.canonical_dir, receipt)
    try:
        rel = canonical_path.relative_to(paths.root).as_posix()
    except Exception:
        rel = canonical_path.as_posix()
    return ReceiptIngestResponse(canonical_receipt_path=rel, receipt=receipt)
