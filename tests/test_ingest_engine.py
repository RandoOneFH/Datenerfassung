from pathlib import Path

from datenerfassung.engine import IngestEngine
from datenerfassung.project_paths import ProjectPaths


def _write_rules(rules_dir: Path) -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)

    (rules_dir / "normalization.yml").write_text(
        "\n".join(
            [
                "version: 1",
                "stopwords: [k, kbio, bio]",
                "synonyms:",
                "  h-milch: milch",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (rules_dir / "merchants.yml").write_text(
        "\n".join(
            [
                "version: 1",
                "merchants:",
                "  - id: kaufland",
                "    names: [kaufland]",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (rules_dir / "categories.yml").write_text(
        "\n".join(
            [
                "version: 1",
                "rules:",
                "  - id: deposit_pfand",
                "    priority: 200",
                "    when:",
                "      any:",
                "        - contains_any: [pfand, pfandartikel]",
                "        - regex: \"\\\\bpfand\\\\b\"",
                "    then:",
                "      category: groceries.deposit",
                "      tags_add: [deposit]",
                "      confidence: 0.99",
                "  - id: household_detergent",
                "    priority: 90",
                "    when:",
                "      any:",
                "        - contains_any: [waschmittel, reiniger, frosch]",
                "    then:",
                "      category: household.cleaning",
                "      confidence: 0.95",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_ingest_text_persists_raw_and_canonical(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    rules_dir = data_dir / "rules"
    _write_rules(rules_dir)

    paths = ProjectPaths(
        root=tmp_path,
        data_dir=data_dir,
        raw_dir=data_dir / "raw",
        canonical_dir=data_dir / "canonical",
        rules_dir=rules_dir,
        schema_dir=tmp_path / "schema",
    )

    engine = IngestEngine(paths)

    result = engine.ingest_text(
        "\n".join(
            [
                "Kaufland",
                "29.12.2025 12:07",
                "Waschmittel 2,99",
                "Pfand 0,25",
            ]
        ),
        source_name="pytest",
    )

    assert result.status == "ok"
    assert result.receipt is not None
    assert any(li.category == "household.cleaning" for li in result.receipt.line_items)
    assert any(li.category == "groceries.deposit" for li in result.receipt.line_items)

    assert (tmp_path / Path(result.ingest_event_path)).exists()
    assert result.raw_text_path is not None
    assert (tmp_path / Path(result.raw_text_path)).exists()
    assert result.canonical_receipt_path is not None
    assert (tmp_path / Path(result.canonical_receipt_path)).exists()


def test_ingest_receipt_json_ingests_structured_payload(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    rules_dir = data_dir / "rules"
    _write_rules(rules_dir)

    paths = ProjectPaths(
        root=tmp_path,
        data_dir=data_dir,
        raw_dir=data_dir / "raw",
        canonical_dir=data_dir / "canonical",
        rules_dir=rules_dir,
        schema_dir=tmp_path / "schema",
    )

    engine = IngestEngine(paths)

    payload = {
        "merchant": {"name": "Kaufland", "store_id": "DE7450"},
        "datetime": "2025-12-29T12:07:00+01:00",
        "currency": "EUR",
        "items": [
            {"name": "KBio H-Milch", "quantity": 6, "unit_price": 1.25, "total": 7.50, "vat_rate": 0.07},
            {"name": "Frosch Waschmittel", "quantity": 1, "unit_price": 4.95, "total": 4.95, "vat_rate": 0.19},
            {"name": "Pfandartikel", "quantity": 1, "unit_price": 0.25, "total": 0.25, "vat_rate": 0.00},
        ],
        "totals": {"total": 12.70, "vat": [{"rate": 0.19, "gross": 4.95}, {"rate": 0.07, "gross": 7.75}]},
        "confidence": "high",
    }

    result = engine.ingest_receipt_json(payload, source_name="pytest")

    assert result.status == "ok"
    assert result.raw_receipt_json_path is not None
    assert (tmp_path / Path(result.raw_receipt_json_path)).exists()
    assert result.receipt is not None
    assert result.receipt.receipt.merchant.store_id == "DE7450"
    assert any(li.category == "household.cleaning" for li in result.receipt.line_items)
    assert any(li.category == "groceries.deposit" for li in result.receipt.line_items)
