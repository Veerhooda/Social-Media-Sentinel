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

For real stored canonical events, run BERTrend separately:

```bash
uv run python scripts/run_trends.py --platform x --allow-model-download
```

Then inspect `/api/analytics/topics` and a returned topic's detail/evolution endpoints.

For Telegram, configure an authorized session locally and use only an explicitly
selected public channel. Keep runs bounded:

```bash
uv run python scripts/run_telegram_history.py public_channel --max-messages 20
uv run python scripts/run_telegram_stream.py --channel public_channel --duration-seconds 30
```

Without all three Telegram settings, both commands report `SKIPPED`. They never
substitute replay data for a live Telegram result.

For the dashboard demo:

```bash
SCHEDULER_ENABLED=true uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. Demographics shows aggregate geography, language, and professional interests with an honest age-unavailable state; Settings remains intentionally unavailable.
