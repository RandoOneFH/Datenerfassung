from __future__ import annotations

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel, Field

from ...engine import IngestEngine
from ...models import IngestResult
from .orchestrator import IngestOrchestrator


class IngestTextRequest(BaseModel):
    text: str = Field(min_length=1)
    source_name: str | None = None


class IngestReceiptJsonRequest(BaseModel):
    receipt: dict
    source_name: str | None = None


app = FastAPI(title="Datenerfassung Ingest Service", version="0.1.0")
engine = IngestEngine()
orchestrator = IngestOrchestrator.detect()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/ingest/text", response_model=IngestResult)
def ingest_text(req: IngestTextRequest) -> IngestResult:
    return orchestrator.ingest_text(req.text, source_name=req.source_name)


@app.post("/ingest/receipt_json", response_model=IngestResult)
def ingest_receipt_json(req: IngestReceiptJsonRequest) -> IngestResult:
    return engine.ingest_receipt_json(req.receipt, source_name=req.source_name)


@app.post("/ingest/image", response_model=IngestResult)
async def ingest_image(
    image: UploadFile = File(...),
    ocr_text: str | None = Form(None),
    source_name: str | None = Form(None),
) -> IngestResult:
    content = await image.read()
    return orchestrator.ingest_image(
        content,
        filename=image.filename,
        ocr_text=ocr_text,
        source_name=source_name,
    )
