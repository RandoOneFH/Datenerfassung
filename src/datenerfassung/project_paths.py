from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _resolve_from_root(root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (root / candidate).resolve()


def find_project_root(start: Path | None = None) -> Path:
    cursor = (start or Path.cwd()).resolve()
    for candidate in [cursor, *cursor.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("Could not find project root (missing pyproject.toml in parent chain).")


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    root: Path
    data_dir: Path
    raw_dir: Path
    canonical_dir: Path
    rules_dir: Path
    schema_dir: Path

    @classmethod
    def detect(cls, start: Path | None = None) -> "ProjectPaths":
        root = find_project_root(start)

        data_dir = _resolve_from_root(root, os.getenv("DATENERFASSUNG_DATA_DIR", "data"))
        rules_dir = _resolve_from_root(root, os.getenv("DATENERFASSUNG_RULES_DIR", str(data_dir / "rules")))
        schema_dir = _resolve_from_root(root, os.getenv("DATENERFASSUNG_SCHEMA_DIR", "schema"))

        raw_dir = data_dir / "raw"
        canonical_dir = data_dir / "canonical"

        return cls(
            root=root,
            data_dir=data_dir,
            raw_dir=raw_dir,
            canonical_dir=canonical_dir,
            rules_dir=rules_dir,
            schema_dir=schema_dir,
        )

    def ensure_dirs(self) -> None:
        (self.raw_dir / "images").mkdir(parents=True, exist_ok=True)
        (self.raw_dir / "ocr_text").mkdir(parents=True, exist_ok=True)
        (self.raw_dir / "ingest_events").mkdir(parents=True, exist_ok=True)
        (self.canonical_dir / "receipts").mkdir(parents=True, exist_ok=True)
        (self.canonical_dir / "items").mkdir(parents=True, exist_ok=True)

