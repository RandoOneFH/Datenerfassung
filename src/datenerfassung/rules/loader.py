from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class NormalizationRules:
    stopwords: set[str]
    synonyms: dict[str, str]


@dataclass(frozen=True, slots=True)
class Merchant:
    id: str
    names: list[str]


@dataclass(frozen=True, slots=True)
class MerchantsRules:
    merchants: list[Merchant]


@dataclass(frozen=True, slots=True)
class CategoryRule:
    id: str
    priority: int
    when_any: list[dict]
    then: dict


@dataclass(frozen=True, slots=True)
class CategoriesRules:
    rules: list[CategoryRule]


@dataclass(frozen=True, slots=True)
class RuleSet:
    normalization: NormalizationRules
    merchants: MerchantsRules
    categories: CategoriesRules

    @classmethod
    def load_from_dir(cls, rules_dir: Path) -> "RuleSet":
        normalization = _load_yaml(rules_dir / "normalization.yml")
        merchants = _load_yaml(rules_dir / "merchants.yml")
        categories = _load_yaml(rules_dir / "categories.yml")

        normalization_rules = NormalizationRules(
            stopwords=set((normalization or {}).get("stopwords") or []),
            synonyms=dict((normalization or {}).get("synonyms") or {}),
        )

        merchants_rules = MerchantsRules(
            merchants=[
                Merchant(id=str(m["id"]), names=[str(n) for n in (m.get("names") or [])])
                for m in ((merchants or {}).get("merchants") or [])
            ]
        )

        category_rules = []
        for rule in ((categories or {}).get("rules") or []):
            category_rules.append(
                CategoryRule(
                    id=str(rule["id"]),
                    priority=int(rule.get("priority") or 0),
                    when_any=list(((rule.get("when") or {}).get("any") or [])),
                    then=dict(rule.get("then") or {}),
                )
            )
        category_rules.sort(key=lambda r: r.priority, reverse=True)

        categories_rules = CategoriesRules(rules=category_rules)

        return cls(
            normalization=normalization_rules,
            merchants=merchants_rules,
            categories=categories_rules,
        )


def _load_yaml(path: Path) -> dict | None:
    if not path.exists():
        raise FileNotFoundError(str(path))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping at {path}, got {type(data).__name__}.")
    return data

