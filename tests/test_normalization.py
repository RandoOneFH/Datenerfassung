from datenerfassung.rules.loader import NormalizationRules
from datenerfassung.rules.normalization import normalize_name


def test_normalize_name_applies_stopwords_and_synonyms() -> None:
    rules = NormalizationRules(
        stopwords={"k", "kbio", "bio"},
        synonyms={"h-milch": "milch", "champignons": "champignon"},
    )

    name_clean, tokens, name_norm = normalize_name("KBio H-Milch", rules)

    assert name_clean == "kbio milch"
    assert tokens == ["milch"]
    assert name_norm == "milch"

