from __future__ import annotations

import argparse
import sys

from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.nlp.service import NLPService
from app.pipeline.service import EventPipeline
from app.platforms.x.adapter import XAdapter
from app.platforms.x.client import XAPIError, XAuthenticationError


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch X recent search and run the analytics pipeline")
    parser.add_argument("--query", default=None, help="Overrides X_QUERY")
    parser.add_argument("--max-results", type=int, default=None)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--stance-target", default=None)
    args = parser.parse_args()

    try:
        search = XAdapter().search_recent(
            args.query,
            max_results=args.max_results,
            max_pages=args.max_pages,
        )
    except (XAPIError, XAuthenticationError) as exc:
        print(f"LIVE X SEARCH: FAIL - {str(exc).replace(chr(10), ' | ')}", file=sys.stderr)
        return 2
    with SessionLocal() as session:
        pipeline = EventPipeline(SocialRepository(session), NLPService())
        for event in search.events:
            print(pipeline.process(event, stance_target=args.stance_target).model_dump_json())
    print(f"pages={search.pages_fetched} events={len(search.events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
