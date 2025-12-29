# household_receipt_service

Receipt parsing + normalization + categorization service for the PoC.

**What it does**
- Parses receipt text, normalizes product names, and applies rule-based categorization
- Persists canonical receipts under `data/canonical/receipts/<year>/`

**Run (local)**
- `python -m uvicorn datenerfassung.services.household_receipt_service.app:app --reload --port 8001`

**Endpoints**
- `GET /healthz`
- `POST /receipts/parse_text` (JSON: `{ "text": "...", "source_type": "text|image", "ingest_event_id": "optional" }`)
- `POST /receipts/ingest_text` (same request; persists and returns `canonical_receipt_path`)
