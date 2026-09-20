# NLP

## Checkpoints

- Sentiment: `cardiffnlp/twitter-roberta-base-sentiment-latest`
- Emotion: `SamLowe/roberta-base-go_emotions`
- Irony: `cardiffnlp/twitter-roberta-base-irony`
- Stance: CardiffNLP fixed-target checkpoints only for configured supported targets

Models load directly through the current Transformers API and run with `torch.no_grad()`.

## Output and persistence

Each result stores the label/distribution, confidence, checkpoint name/version marker, and analysis timestamp. GoEmotions native scores are retained. `nervousness` is additionally exposed as the product term `anxiety`; it is not described as a native GoEmotions label.

Irony is presented as an irony classifier. The implementation does not claim perfect or universal sarcasm detection.

## Stance boundary

The fixed-target analyzer supports only:

- abortion
- atheism
- climate
- feminist
- hillary

An arbitrary target returns `supported=false` with an explicit reason. `GeneralTargetStanceAnalyzer` is an interface placeholder and remains unavailable until a general NLI/stance checkpoint is validated. Sentiment is never substituted for stance.

## Verification

Real model smoke inference on 2026-09-20:

- Sentiment: PASS, positive result with all three required labels.
- Emotion: PASS, primary `excitement`; `anxiety=0.2890` mapped from native nervousness.
- Irony: PASS, `is_ironic=true`, confidence `0.9923` for the smoke sentence.
- Fixed-target stance: PASS for `climate`, label `favor`, confidence `0.8380`, with `against`/`favor`/`none` scores.

These values prove model loading/schema execution only; they are not accuracy benchmarks.
