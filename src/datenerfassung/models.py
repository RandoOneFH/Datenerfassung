from __future__ import annotations

from pydantic import BaseModel, Field


class ReceiptMerchant(BaseModel):
    id: str | None = None
    name: str | None = None
    store_id: str | None = None


class ReceiptInfo(BaseModel):
    id: str
    merchant: ReceiptMerchant
    datetime: str
    currency: str = "EUR"
    payment_method: str | None = None


class LineItemClassification(BaseModel):
    engine: str = "rules"
    rule_id: str | None = None
    confidence: float | None = None


class LineItem(BaseModel):
    line_id: str
    name_raw: str
    name_clean: str | None = None
    tokens: list[str] = Field(default_factory=list)
    name_norm: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total: float | None = None
    vat_rate: float | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    classification: LineItemClassification | None = None


class VatBreakdownItem(BaseModel):
    rate: float
    gross: float


class Totals(BaseModel):
    total: float | None = None
    vat_breakdown: list[VatBreakdownItem] = Field(default_factory=list)


class Provenance(BaseModel):
    source_type: str
    ocr_engine: str | None = None
    parser: str = "de_receipt_v1"
    created_at: str
    ingest_event_id: str | None = None


class CanonicalReceipt(BaseModel):
    schema_version: str = "1.0"
    receipt: ReceiptInfo
    line_items: list[LineItem]
    totals: Totals
    provenance: Provenance


class IngestResult(BaseModel):
    ingest_event_id: str
    status: str
    raw_text_path: str | None = None
    raw_receipt_json_path: str | None = None
    raw_image_path: str | None = None
    ingest_event_path: str
    canonical_receipt_path: str | None = None
    receipt: CanonicalReceipt | None = None
