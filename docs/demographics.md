# Demographics

Aggregate, anonymized demographic estimation over the existing X + Telegram
dataset. Implemented 2026-09-21. No external platform calls were made; all
signals derive from stored public profile indicators, bio text, and event
content already in PostgreSQL.

## What is inferred versus observed

- Language: platform-observed `language_code` is preferred where present
  (observed metadata, confidence 1.0). Otherwise `langdetect` text
  identification with minimum-text, emoji-only, URL-only, and ambiguity
  guards. Short or ambiguous inputs return unknown.
- Geography: deterministic normalization of raw public `location_raw`
  strings into country/region buckets. Stored as ISO-style country codes
  (`VARCHAR(8)`); labels resolved at read time. No geocoding, no precise
  residence, no home-address inference.
- Professional interests: keyword-anchored sector classification over a
  controlled taxonomy (Technology, Education, Finance, Healthcare, Business,
  Media, Government, Research, Other, Unknown). These are inferred interest
  sectors, not verified occupations. Professions are never invented from
  usernames alone; empty bios yield Unknown. A semantic backend reusing the
  cached `all-MiniLM-L12-v2` embedding is available behind the same
  interface; the default deterministic keyword backend requires no model
  download.
- Age: UNAVAILABLE. No validated age model is configured and the available
  evidence cannot support credible brackets. The interface
  (`app/demographics/age.py`) is ready for a future validated model, but the
  aggregate dimension reports UNAVAILABLE rather than fabricated brackets.
  Legacy M3Inference was deliberately not forced into the Python 3.13
  runtime.

## Confidence and uncertainty

Every persisted prediction carries confidence where meaningful, an inference
source, and per-dimension model versions (`model_versions` JSONB). Unknown
cohorts are always included in aggregates, never silently dropped.

## Aggregate-only presentation

The API (`GET /api/analytics/demographics` plus per-dimension endpoints)
returns counts, shares, mean confidence, and unknown counts. No endpoint
exposes per-user demographic profiles. The dashboard Demographics screen
shows horizontal-bar distributions with unknown/insufficient-data states and
confidence context. No profile cards, no individual ages, locations, or jobs.

## Current corpus results (local, 280 subjects)

- Language: AVAILABLE — en 100% (X payload codes observed; Telegram texts identified).
- Geography: AVAILABLE — 75% unknown; India 8.2%, United States 6.4%, United Kingdom 4.3%.
- Profession: AVAILABLE — Technology leading; 27.9% unknown; remainder across Media, Research, Education, Business, Government, Finance, Other.
- Age: UNAVAILABLE — 100% unknown by design (see feasibility spike 2026-09-21 below).

## Age feasibility spike (2026-09-21)

Outcome: NOT CREDIBLE WITH CURRENT DATA. AGE remains UNAVAILABLE.

Local evidence audit (280 users, 305 events, read-only):

- Display names present for all 280 users, bios for 225, locations for 154.
- Zero bios contain explicit age cues (no "24yo", "aged 30", graduation years).
- Only 9 of 225 bios contain weak life-stage keywords (student, retired, etc.).
- Only 1 user has 5 or more events, so behavioral/activity features are
  effectively absent (median contribution is a single short post).
- `avatar_url` holds remote URLs for 274 users; no image bytes are stored.
  Downloading profile photos would be new external collection plus face
  processing, which this milestone forbids and privacy policy discourages.

Candidates evaluated (metadata and implementation inspected, no large
downloads, no README-only trust):

1. M3Inference 1.1.5 (euagendas/m3inference, AGPL-3.0) — REJECTED.
   Best accuracy requires profile images we do not store; the pipeline
   downloads and resizes 400x400 photos. Install targets the Python 3.6 era
   with a `pycld2` C++ dependency, training data is 2019 Twitter (domain
   drift to current X/Telegram), and with zero ground-truth ages in our
   corpus its accuracy on our data is unmeasurable. Forcing it into the
   Python 3.13 runtime is not defensible.
2. kaantureyyen/deberta-blog-authorship-corpus-age — REJECTED. Zero likes,
   single-digit downloads, labels are undocumented generics (LABEL_0/1/2
   with no age mapping), no evaluation report, and it is trained on the
   2004 long-form English Blog Authorship Corpus — severe domain mismatch
   with short multilingual social posts.
3. mrm8488/bert-mini-finetuned-age_news-classification and
   mpapucci/bert-age-classification-tag-it — REJECTED. The former is an
   AG-News-trained recency-style classifier, not a human-age model; the
   latter has no model card, no documented labels, and negligible adoption.
4. dima806/fairface_age_image_detection (ViT, Apache-2.0) — REJECTED for
   this corpus. Credible machinery, but it needs face image bytes and our
   evidence audit shows we store only remote URLs. Using it would require
   new image collection outside this milestone's scope.
5. Keyword/life-stage heuristics ("student" implies young) — REJECTED.
   Coverage is 4% of bios and the mapping from words to brackets is
   stereotyping, not inference. Implementing it would only make the UI
   green while fabricating results.

The stable interface (`app/demographics/age.py`, `AgeModel` protocol,
`UNAVAILABLE` aggregate status) is retained for a future validated model.
A credible future path needs either stored, consented age signals or a
validated text model whose accuracy can be measured against labeled data
from the same distribution — neither exists today.


## Limitations

- Keyword profession signals are heuristic interest indicators, not ground truth.
- Geography covers only normalizable public strings; 75% of the current corpus is unknown.
- Language identification on short social posts is approximate; ambiguous results return unknown.
- No exact age, no exact residence, no salary, no sensitive attributes — by design, not by omission.
