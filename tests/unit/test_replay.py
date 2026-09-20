from pathlib import Path

from app.replay.loader import ReplayLoader


def test_replay_is_explicitly_labeled() -> None:
    path = Path(__file__).parents[2] / "data" / "replay" / "x_synthetic.jsonl"
    events = ReplayLoader().load(path)
    assert len(events) == 4
    assert all(event.platform == "x" for event in events)
    assert all(event.source_metadata["replay"] is True for event in events)

