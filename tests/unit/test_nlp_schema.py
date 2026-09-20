from datetime import UTC, datetime

from app.nlp.schemas import (
    ClassificationResult,
    EmotionResult,
    IronyResult,
    NLPResult,
    StanceResult,
)


def test_nlp_output_keeps_native_nervousness_and_mapped_anxiety() -> None:
    result = NLPResult(
        sentiment=ClassificationResult(
            label="neutral", confidence=0.7, scores={"neutral": 0.7}, model_name="m1", model_version="v1"
        ),
        emotions=EmotionResult(
            primary_label="anxiety",
            scores={"nervousness": 0.8, "anxiety": 0.8},
            native_scores={"nervousness": 0.8},
            model_name="m2",
            model_version="v2",
        ),
        irony=IronyResult(
            is_ironic=False, confidence=0.1, scores={"irony": 0.1}, model_name="m3", model_version="v3"
        ),
        stance=StanceResult(supported=False, reason="unsupported"),
        processed_at=datetime.now(UTC),
    )
    assert result.emotions.native_scores["nervousness"] == result.emotions.scores["anxiety"]
    assert result.stance.label is None

