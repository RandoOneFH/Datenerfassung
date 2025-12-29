from __future__ import annotations

import re

from .loader import CategoriesRules, CategoryRule


def categorize(name_clean: str, tokens: list[str], rules: CategoriesRules) -> tuple[str, str | None, float | None, list[str]]:
    for rule in rules.rules:
        if _matches(rule, name_clean, tokens):
            category = str(rule.then.get("category") or "other")
            confidence = rule.then.get("confidence")
            tags_add = list(rule.then.get("tags_add") or [])
            return category, rule.id, float(confidence) if confidence is not None else None, tags_add
    return "other", None, None, []


def _matches(rule: CategoryRule, name_clean: str, tokens: list[str]) -> bool:
    for condition in rule.when_any:
        if "regex" in condition and _matches_regex(str(condition["regex"]), name_clean):
            return True
        if "contains_any" in condition and _matches_contains_any(list(condition["contains_any"]), name_clean, tokens):
            return True
    return False


def _matches_regex(pattern: str, name_clean: str) -> bool:
    return re.search(pattern, name_clean) is not None


def _matches_contains_any(values: list[str], name_clean: str, tokens: list[str]) -> bool:
    token_set = set(tokens)
    for value in values:
        v = str(value)
        if v in token_set:
            return True
        if v and v in name_clean:
            return True
    return False

