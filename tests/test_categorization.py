from datenerfassung.rules.categorization import categorize
from datenerfassung.rules.loader import CategoriesRules, CategoryRule


def test_categorize_pfand_by_regex() -> None:
    rules = CategoriesRules(
        rules=[
            CategoryRule(
                id="deposit_pfand",
                priority=200,
                when_any=[{"regex": "\\bpfand\\b"}],
                then={"category": "groceries.deposit", "tags_add": ["deposit"], "confidence": 0.99},
            )
        ]
    )

    category, rule_id, confidence, tags_add = categorize("pfand flasche", ["pfand", "flasche"], rules)

    assert category == "groceries.deposit"
    assert rule_id == "deposit_pfand"
    assert confidence == 0.99
    assert tags_add == ["deposit"]

