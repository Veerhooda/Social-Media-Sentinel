from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": getattr(record, "service", record.name),
            "platform": getattr(record, "platform", None),
            "event_id": getattr(record, "event_id", None),
            "operation": getattr(record, "operation", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "status": getattr(record, "status", record.levelname),
            "error": getattr(record, "error", None),
            "message": record.getMessage(),
        }
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

