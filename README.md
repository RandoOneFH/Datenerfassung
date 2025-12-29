# Datenerfassung

Self-hosted, Python-based ingest system for automated household data capture (receipts: image/text ingest → OCR → parsing → normalization → rule-based categorization) with JSON-file persistence.

## Status
PoC / MVP scaffold. Focus: **data quality, deterministic normalization, explainable rules**, and **raw + canonical storage**.

## Project structure (high level)
- `services/ingest_service/` – general ingest (accepts image/text, stores raw, routes downstream)
- `services/household_receipt_service/` – receipt parsing + normalization + categorization
- `data/` – JSON-file persistence (raw + canonical)
- `docs/` – requirements/specs
- `schema/` – JSON schema definitions
- `data/rules/` – rule files (categorization, normalization, merchants)

## Quickstart (local)
Prerequisites: Python 3.11+

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .[dev]
```

## Run (local)
- Receipt API: `python -m uvicorn datenerfassung.services.household_receipt_service.app:app --reload --port 8001`
- Ingest API: `python -m uvicorn datenerfassung.services.ingest_service.app:app --reload --port 8000`

## Docs
- `docs/household_ingest_poc.md`

## License
TBD
