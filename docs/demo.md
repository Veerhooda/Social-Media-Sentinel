# Demo Runbook

Judge walkthrough on the local corpus. No credentials, no external calls,
no collection, no model downloads. Start with `./scripts/demo.sh`, then open
`http://127.0.0.1:5173`.

## STEP 1 — Open Overview

Click Overview. Notice total real events, sentiment shift, and topics from
stored X + Telegram data. Demonstrates the unified timeline (PS A).

## STEP 2 — Show source status

Scroll to Data Sources. X and Telegram show stored real-event counts;
YouTube/Reddit show COMING SOON; Meta shows PLANNED. No fake throughput.
Demonstrates honest collection state (PS A).

## STEP 3 — Show Live Feed

Open Live Feed. Rows are chronological canonical events with persisted NLP.
The REAL DATA / MIXED DATA badge reflects stored rows, not an active
collector. Demonstrates normalization and persistence (PS A).

## STEP 4 — Show Sentiment & Emotion

Open Sentiment & Emotion. Point out positive/neutral/negative over time,
anxiety labeled as a nervousness mapping, and the irony-is-not-sarcasm note.
Demonstrates nuanced inference with uncertainty (PS B).

## STEP 5 — Show Trends & Topic Evolution

Open Trends & Topics. Show ranked topics with growth and velocity, then open
a topic to show its evolution chart. Note where status reads
INSUFFICIENT_DATA: one measurement is never called a trend. Demonstrates
temporal topic detection without fabricated virality (PS D).

## STEP 6 — Show Network Analysis

Open Network Analysis. Show nodes, edges, communities, and the structural
influence table. Language is "structural influence", never causal control.
Demonstrates interaction topology (PS E).

## STEP 7 — Show observed cascade

In Network Analysis, open the cascades panel and select the largest cascade.
Walk the chronological propagation path with community and sentiment per
step. Note any "partially observable" provenance. Demonstrates observed
propagation without invented edges (PS E).

## STEP 8 — Show Demographics

Open Demographics. Show geography, language, and professional-interest bars
with unknown cohorts and confidence context. Sectors are labeled inferred
interests, not verified jobs. Demonstrates aggregate profiling (PS C).

## STEP 9 — Explain age-unavailable state

On the same screen, show the Age panel: Dimension unavailable, with the
one-line explanation that the corpus lacks validated age evidence. Full
reasoning lives in `docs/demographics.md`. Demonstrates refusal to fabricate
(PS C).

## STEP 10 — Return to Overview

Close on the honest system picture: what is observed, what is inferred,
what is unavailable. Replay rows, if any, are badged REPLAY throughout.

## Reproducing the demo state

The standard demo is read-only over the existing PostgreSQL corpus.
`scripts/demo_check.py` validates the environment (7 checks) without
contacting platforms or downloading models. For an empty database, load
labeled replay fixtures without external calls:

```bash
uv run python scripts/run_replay.py
```

Replay data is synthetic and always labeled as replay. Never present it as
live platform data. Live X/Telegram ingestion is configured separately (see
README) and is never part of the standard demo.
