from app.nlp.stance import FixedTargetStanceAnalyzer, GeneralTargetStanceAnalyzer


def test_fixed_target_analyzer_rejects_arbitrary_target_without_inference() -> None:
    result = FixedTargetStanceAnalyzer().analyze("text", "new emerging subject")
    assert result.supported is False
    assert "Unsupported arbitrary target" in result.reason


def test_general_target_path_is_explicitly_unavailable_until_validated() -> None:
    result = GeneralTargetStanceAnalyzer().analyze("text", "new emerging subject")
    assert result.supported is False
    assert "not yet been validated" in result.reason

