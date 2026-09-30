# Prototype recording narration

The 1 minute 51.57 second walkthrough follows the user's actual prototype recording. Its original 2752×1548 H.264 video at 60 fps is copied without visual edits, retiming, or re-encoding. Only a stereo AAC narration track is added. There is no music bed or extra animation.

The voice is synthetic English narration (Emma Neural) with conversational wording. Each passage was generated separately and measured against its screen interval. Overlong passages were rewritten; no speech was time-stretched. This keeps explanations aligned with navigation while preserving the recording.

Generated recordings and audio remain local under the ignored `output/recording-voiceover/` directory. They are not included in the Git repository because they contain collected public social content and large media files. The exported filename is `Social-Sentinel-Prototype-Narrated.mp4`.

## Spoken script

| Time | Visible content | Narration |
|---|---|---|
| 0:00–0:13 | Landing page | Meet Social Sentinel, by Team Icarus. What are people feeling? Which conversations are changing? And who's connecting them? We bring those questions together on one timeline. Let's take a look. |
| 0:13–0:32 | Overview | Here's the working dashboard: three hundred and one real events from X and public Telegram channels. Four replay records are labeled separately. You can explore sentiment, emotion, activity and discovered topics together, with every view grounded in the conversations we've actually collected. |
| 0:32–0:43 | Conversation feed | Want the context behind a number? Open the feed. Posts, timestamps, engagement and model results sit side by side. Filter the discussion, then inspect the evidence. |
| 0:43–0:59 | Sentiment and emotion | Now, follow the mood over time. Positive, neutral and negative sentiment stay separate from finer emotions and irony. Hover to inspect each window. These are model estimates, and general topic stance stays unavailable until we have a validated approach. |
| 0:59–1:07 | Topic ranking | Next, topics. B E R Trend groups the collected text into discussions, then tracks volume and change across source time windows. |
| 1:07–1:15 | Topic detail | This topic has one observation, so growth stays unavailable. Comparable history comes first. Then we can measure change. |
| 1:15–1:33 | Interaction map | Here's where the conversation connects. Select an account, and its observed links come into focus. Replies, mentions and reposts reveal interaction patterns, while PageRank helps identify structurally central accounts. You can inspect the actual relationships behind each node, right here. |
| 1:33–1:38 | Demographics | Audience estimates stay aggregate, with unknowns visible and age unavailable. |
| 1:38–1:43 | Timeline | The timeline brings those observations back into their original chronological order. |
| 1:43–1:49 | Data sources | Source status shows what's collected, configured, and coming next. That's Social Sentinel. |
| 1:49–1:52 | Collection status | We're Team Icarus. |

## Accuracy

The video demonstrates stored data rather than an active collection session. The topic detail shown has insufficient temporal history, so narration does not describe it as a demonstrated rising trend. Network language refers to observed interactions and structural centrality. Age inference and general-target stance remain unavailable. No live YouTube collection is claimed.

## Repository verification before publishing

Executed on 30 September 2026:

- `uv run pytest -q`: 123 passed, one upstream Starlette/AnyIO deprecation warning.
- `uv run ruff check app tests scripts`: all checks passed.
- `uv run alembic check`: no new upgrade operations detected.
- `npm test -- --run` in `frontend`: 21 passed across 11 files.
- `npm run lint` and `npm run build` in `frontend`: passed.
- `git diff --check`: passed.

These checks verify the local implementation and build. They do not reverify live external platform access or model accuracy.
