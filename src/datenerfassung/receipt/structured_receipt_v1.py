from __future__ import annotations

from pydantic import BaseModel, Field


class StructuredMerchant(BaseModel):
    name: str | None = None
    address: str | None = None
    store_id: str | None = None


class StructuredItem(BaseModel):
    name: str = Field(min_length=1)
    quantity: float | None = None
    unit_price: float | None = None
    total: float | None = None
    vat_rate: float | None = None


class StructuredVatLine(BaseModel):
    rate: float
    net: float | None = None
    vat: float | None = None
    gross: float | None = None


class StructuredTotals(BaseModel):
    total: float | None = None
    vat: list[StructuredVatLine] = Field(default_factory=list)
    payment_method: str | None = None


class StructuredReceiptV1(BaseModel):
    merchant: StructuredMerchant = Field(default_factory=StructuredMerchant)
    datetime: str | None = None
    currency: str | None = "EUR"
    items: list[StructuredItem] = Field(default_factory=list)
    totals: StructuredTotals = Field(default_factory=StructuredTotals)
    confidence: str | None = None

