from __future__ import annotations

from app.nlp.emotion import EmotionAnalyzer
from app.nlp.irony import IronyAnalyzer
from app.nlp.sentiment import SentimentAnalyzer
from app.nlp.stance import FixedTargetStanceAnalyzer


def run(name: str, operation) -> bool:
    try:
        result = operation()
        print(f"PASS        {name:<20} {result}")
        return True
    except Exception as exc:
        print(f"UNAVAILABLE {name:<20} {type(exc).__name__}: {exc}")
        return False


def sentiment() -> str:
    result = SentimentAnalyzer(allow_download=True).analyze("I am pleased with the result.")
    required = {"positive", "neutral", "negative"}
    if not required.issubset(result.scores):
        raise RuntimeError(f"missing expected labels: {required - set(result.scores)}")
    return f"label={result.label}; labels={sorted(result.scores)}"


def emotion() -> str:
    result = EmotionAnalyzer(allow_download=True).analyze("I am nervous but excited.")
    if "nervousness" not in result.native_scores or "anxiety" not in result.scores:
        raise RuntimeError("nervousness -> anxiety mapping is missing")
    return f"primary={result.primary_label}; anxiety={result.scores['anxiety']:.4f}"


def irony() -> str:
    result = IronyAnalyzer(allow_download=True).analyze("Wonderful, another outage.")
    if not ({"irony", "ironic"} & set(result.scores)):
        raise RuntimeError(f"missing irony label: {sorted(result.scores)}")
    return f"is_ironic={result.is_ironic}; confidence={result.confidence:.4f}"


def stance() -> str:
    result = FixedTargetStanceAnalyzer(allow_download=True).analyze(
        "Climate action should be accelerated.", "climate"
    )
    if not result.supported or set(result.scores) != {"against", "favor", "none"}:
        raise RuntimeError(f"unexpected fixed-target stance output: {result}")
    return f"target={result.target}; label={result.label}; confidence={result.confidence:.4f}"


def main() -> int:
    results = [
        run("sentiment", sentiment),
        run("emotion", emotion),
        run("irony", irony),
        run("fixed-target stance", stance),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
