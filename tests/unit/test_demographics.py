"""Deterministic unit tests for aggregate demographic inference."""
from uuid import uuid4

from app.demographics.age import AgeAnalyzer
from app.demographics.geography import bucket_label, normalize_location
from app.demographics.language import identify_language, user_language
from app.demographics.profession import SectorClassifier
from app.demographics.schemas import UserDemographicSignal
from app.demographics.service import DemographicService


def _signal(**overrides):
    base = {
        "user_id": uuid4(),
        "platform": "x",
        "age_bracket": None,
        "age_confidence": None,
        "age_source": "age-unavailable-v1",
        "country": None,
        "region": None,
        "geography_confidence": None,
        "geography_source": "unknown",
        "language": None,
        "language_confidence": None,
        "language_source": "unknown",
        "professional_sector": None,
        "profession_confidence": None,
        "profession_source": "unknown",
    }
    base.update(overrides)
    return UserDemographicSignal(**base)


def test_platform_language_is_trusted_without_overclaiming() -> None:
    result = identify_language("short", platform_language="en")
    assert result.language == "en"
    assert result.confidence == 1.0
    assert result.source == "platform_observed"


def test_short_text_returns_unknown_language() -> None:
    result = identify_language("hi 👍 https://t.co/x @user")
    assert result.language is None
    assert result.source == "unknown"


def test_emoji_only_text_returns_unknown_language() -> None:
    result = identify_language("🎉🔥🚀🚀🚀")
    assert result.language is None


def test_english_sentence_detects_english() -> None:
    text = "The latest benchmark results show astonishing progress across the entire industry today."
    result = identify_language(text)
    assert result.language == "en"
    assert result.confidence is not None and result.confidence >= 0.55


def test_user_language_prefers_platform_code() -> None:
    result = user_language(["short"], platform_languages=[None, "en"])
    assert result.language == "en"
    assert result.source == "platform_observed"


def test_user_language_unknown_without_evidence() -> None:
    result = user_language(["hi"], platform_languages=[None])
    assert result.language is None


def test_geography_normalizes_country() -> None:
    result = normalize_location("Mumbai, India")
    assert result.country_code == "IN"
    assert result.country_label == "India"
    assert result.region == "Maharashtra"
    assert bucket_label(result) == "India"


def test_geography_empty_is_unknown() -> None:
    assert normalize_location(None).country_code is None
    assert normalize_location("   ").source == "unknown"


def test_geography_ambiguous_is_unknown() -> None:
    assert normalize_location("Earth").country_code is None
    assert normalize_location("Worldwide").country_code is None


def test_geography_unsupported_is_unknown() -> None:
    result = normalize_location("Atlantis, Ocean")
    assert result.country_code is None
    assert "unsupported" in result.reason


def test_geography_emoji_only_is_unknown() -> None:
    assert normalize_location("🇮🇳🇮🇳").country_code is None


def test_age_returns_unknown_without_validated_model() -> None:
    analyzer = AgeAnalyzer()
    assert not analyzer.available
    result = analyzer.analyze("AI researcher with ten years of experience", ["some text"])
    assert result.bracket is None
    assert result.confidence is None


def test_age_rejects_out_of_taxonomy_brackets() -> None:
    class Rogue:
        name = "rogue"

        def predict(self, bio, texts):  # noqa: ANN001, ANN202
            from app.demographics.age import AgeResult

            return AgeResult(bracket="25", confidence=0.9, source="rogue")

    result = AgeAnalyzer(model=Rogue()).analyze(None, [])
    assert result.bracket is None


def test_profession_keyword_classifies_technology_bio() -> None:
    classifier = SectorClassifier(backend="keyword")
    result = classifier.classify("Software developer working on machine learning infrastructure", ["I ship code daily"])
    assert result.sector == "Technology"
    assert result.confidence is not None


def test_profession_never_invents_from_username_only() -> None:
    classifier = SectorClassifier(backend="keyword")
    result = classifier.classify("", [])
    assert result.sector is None


def test_profession_short_bio_is_unknown() -> None:
    classifier = SectorClassifier(backend="keyword")
    result = classifier.classify("blog", [])
    assert result.sector is None


def test_profession_semantic_backend_with_stub_embedder() -> None:
    class StubEmbedder:
        def encode(self, texts):  # noqa: ANN001, ANN202
            vectors = []
            for text in texts:
                lowered = text.lower()
                tech = float(sum(word in lowered for word in ("software", "developer", "engineer", "technology")))
                vectors.append([tech, 1.0 - tech if tech else 1.0])
            return vectors

    classifier = SectorClassifier(backend="semantic", embedder=StubEmbedder())
    result = classifier.classify("software engineer building developer tools", ["technology post"])
    assert result.sector in ("Technology", "Other")
    assert "semantic" in result.source


def test_aggregation_reports_unknown_counts() -> None:
    service = DemographicService(sector_classifier=SectorClassifier(backend="keyword"))
    signals = [
        _signal(language="en", language_confidence=1.0, country="India", geography_confidence=0.9,
                professional_sector="Technology", profession_confidence=0.7),
        _signal(),
    ]
    response = service.aggregate(signals)
    assert response.total_subjects == 2
    assert response.dimensions["age"].status == "UNAVAILABLE"
    assert response.dimensions["age"].unknown_count == 2
    assert response.dimensions["language"].status == "AVAILABLE"
    assert response.dimensions["language"].unknown_count == 1
    assert {segment.label for segment in response.dimensions["geography"].segments} == {"India", "Unknown"}
    assert response.status == "AVAILABLE"


def test_empty_aggregation_is_insufficient_data() -> None:
    response = DemographicService().aggregate([])
    assert response.status == "INSUFFICIENT_DATA"
    assert all(dim.status == "INSUFFICIENT_DATA" for dim in response.dimensions.values())


def test_aggregate_output_contains_no_user_identifiers() -> None:
    service = DemographicService()
    response = service.aggregate([_signal(language="en", language_confidence=1.0)])
    dumped = response.model_dump_json()
    assert "platform_user_id" not in dumped
    assert "username" not in dumped
    assert "bio" not in dumped
