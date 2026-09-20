from types import SimpleNamespace

import pytest

from app.platforms.x.stream import XFilteredStream, XStreamRunner


def test_filtered_stream_maps_response_through_canonical_mapper(x_response_payload) -> None:
    observed = []
    stream = XFilteredStream("synthetic-token", observed.append)
    response = SimpleNamespace(
        data=x_response_payload["data"][0],
        includes=x_response_payload["includes"],
    )
    stream.on_response(response)

    assert len(observed) == 1
    assert observed[0].platform_post_id == "2002"
    assert observed[0].source_metadata["collection_mode"] == "filtered_stream"


class FakeRuleStream:
    def __init__(self):
        self.deleted = []
        self.added = []

    def get_rules(self):
        return SimpleNamespace(
            data=[
                SimpleNamespace(id="unrelated", tag="another-service"),
                SimpleNamespace(id="managed", tag="social-sentinel:old"),
            ]
        )

    def delete_rules(self, ids):
        self.deleted.extend(ids)

    def add_rules(self, rules):
        self.added.extend(rules)

    def disconnect(self):
        return None


def test_stream_rule_management_preserves_unrelated_rules() -> None:
    stream = FakeRuleStream()
    runner = XStreamRunner(stream)  # type: ignore[arg-type]

    runner.replace_rules(["#one", "#two"])

    assert stream.deleted == ["managed"]
    assert [rule.value for rule in stream.added] == ["#one", "#two"]
    assert all(rule.tag.startswith("social-sentinel:") for rule in stream.added)


def test_stream_requires_non_empty_rule() -> None:
    stream = FakeRuleStream()
    with pytest.raises(ValueError, match="non-empty"):
        XStreamRunner(stream).replace_rules([" "])  # type: ignore[arg-type]


def test_clear_managed_rules_preserves_unrelated_rules() -> None:
    stream = FakeRuleStream()
    XStreamRunner(stream).clear_managed_rules()  # type: ignore[arg-type]
    assert stream.deleted == ["managed"]
