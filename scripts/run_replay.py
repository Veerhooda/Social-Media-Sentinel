from __future__ import annotations

import argparse

from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.nlp.service import NLPService
from app.pipeline.service import EventPipeline
from app.replay.loader import ReplayLoader


def main() -> int:
    parser = argparse.ArgumentParser(description="Run clearly labeled canonical replay events")
    parser.add_argument("path", nargs="?", default="data/replay/x_synthetic.jsonl")
    parser.add_argument("--stance-target", default=None)
    args = parser.parse_args()

    events = ReplayLoader().load(args.path)
    with SessionLocal() as session:
        pipeline = EventPipeline(SocialRepository(session), NLPService())
        for event in events:
            result = pipeline.process(event, stance_target=args.stance_target)
            print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

