from __future__ import annotations

import json
from pathlib import Path

from app.models.events import CanonicalEvent


class ReplayLoader:
    def load(self, path: str | Path) -> list[CanonicalEvent]:
        source = Path(path)
        events: list[CanonicalEvent] = []
        with source.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                payload = json.loads(line)
                metadata = dict(payload.get("source_metadata") or {})
                metadata.update({"replay": True, "replay_dataset": source.name})
                payload["source_metadata"] = metadata
                try:
                    events.append(CanonicalEvent.model_validate(payload))
                except Exception as exc:
                    raise ValueError(f"Invalid replay event at {source}:{line_number}: {exc}") from exc
        return events

