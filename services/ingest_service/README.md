# ingest_service

General ingest service (text/image) for the PoC.

**What it does**
- Accepts raw text (`/ingest/text`) and images (`/ingest/image`)
- Persists raw inputs under `data/raw/`
- Runs OCR on images (PaddleOCR, if available) and detects “likely receipt”
- Forwards receipt text to `household_receipt_service` for parsing/normalization + canonical persistence
- Falls back to local parsing/persistence if the receipt service is not reachable (configurable)

**Run (local)**
- `python -m uvicorn datenerfassung.services.ingest_service.app:app --reload --port 8000`

**Endpoints**
- `GET /healthz`
- `POST /ingest/text` (JSON: `{ "text": "...", "source_name": "optional" }`)
- `POST /ingest/receipt_json` (JSON: `{ "receipt": { ... }, "source_name": "optional" }`)
- `POST /ingest/image` (multipart: `image` file, optional `ocr_text`, optional `source_name`)

**Config**
- `HOUSEHOLD_RECEIPT_SERVICE_URL` (default `http://127.0.0.1:8001`)
- `INGEST_LOCAL_FALLBACK` (default `1`)

**OCR Setup**
- Install PaddleOCR in your Python environment to enable `/ingest/image`.
- If PaddleOCR is not available, `/ingest/image` will store the raw image and return `stored_raw_image` unless you provide `ocr_text`.
