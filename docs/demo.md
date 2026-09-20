# Replay Demo

Synthetic X-shaped canonical events live in `data/replay/x_synthetic.jsonl`. Every record is labeled as replay.

After PostgreSQL migration and model setup:

```bash
uv run python scripts/run_replay.py
uv run uvicorn app.main:app
```

Inspect:

- `/api/health`
- `/api/events`
- `/api/events/live` (must say replay)
- `/api/analytics/sentiment`
- `/api/analytics/emotions`
- `/api/analytics/trends`
- `/api/network/summary`

