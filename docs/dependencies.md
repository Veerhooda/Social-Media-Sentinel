# Dependencies

Verified on 2026-09-20 using CPython 3.13.11 on macOS arm64.

| Component | Installed version | Python requirement / role | Verification |
|---|---:|---|---|
| Python | 3.13.11 | Primary runtime | PASS |
| PostgreSQL | 16.14 | Timeline/persistence | PASS: connection and migration |
| Pydantic | 2.13.5 | Canonical/API schemas | PASS |
| FastAPI | 0.141.1 | HTTP API | PASS |
| Uvicorn | 0.53.0 | ASGI server | PASS |
| Tweepy | 4.17.0 | X recent search/stream | PASS: import and interface tests |
| Transformers | 4.57.6 | Direct model loading | PASS |
| PyTorch | 2.14.0 | Model inference | PASS |
| NetworkX | 3.6.1 | Graph analytics | PASS: PageRank and test suite |
| BERTrend | 0.4.18 | Later topic/trend service | PASS: import only |
| SQLAlchemy | 2.0.54 | Repository/data access | PASS |
| Psycopg | 3.3.6 | PostgreSQL driver | PASS |

`uv sync --extra dev --extra trend` resolves 304 packages on Python 3.13. BERTrend has a large transitive dependency footprint and imported successfully; this milestone does not pretend that importing it is equivalent to implementing or validating a BERTrend topic pipeline.

Model smoke tests executed real inference for:

- `cardiffnlp/twitter-roberta-base-sentiment-latest`: PASS; expected labels present.
- `SamLowe/roberta-base-go_emotions`: PASS; native `nervousness` and mapped `anxiety` present.
- `cardiffnlp/twitter-roberta-base-irony`: PASS; binary irony score present.
- `cardiffnlp/twitter-roberta-base-stance-climate`: PASS; `against`/`favor`/`none` labels present.

M3Inference and other legacy demographic dependencies are intentionally absent from the modern environment.

## Verification record

- `uv run pytest -q`: **24 passed**, with one upstream Starlette/AnyIO deprecation warning.
- `uv run ruff check app scripts tests migrations`: **all checks passed**.
- `uv run alembic check`: **no new upgrade operations detected**.
- PostgreSQL migration `0001_x_first`: **applied successfully**.
- Real replay run: **4 events stored, 4 NLP results produced, 4 relationship records created**; a second run reported all **4 as duplicates**.
- Required FastAPI checks: **7/7 returned HTTP 200**.
- Live X verification: **10 Recent Search events plus 4 bounded-stream events stored**, **14 real NLP results**, **15 real interaction edges**, and **10/10 deliberate duplicate reprocesses rejected**.
