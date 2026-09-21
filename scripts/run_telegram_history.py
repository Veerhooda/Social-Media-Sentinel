from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.nlp.service import NLPService
from app.pipeline.service import EventPipeline
from app.platforms.telegram.adapter import TelegramAdapter
from app.platforms.telegram.client import TelegramAPIError, TelegramAuthenticationError
from app.platforms.telegram.models import TelegramCheckpoint


async def run(args: argparse.Namespace) -> int:
    adapter = TelegramAdapter()
    health = adapter.configuration_health()
    if not health.configured:
        print(json.dumps({"status": "SKIPPED", "detail": health.detail}))
        return 0
    checkpoint = (
        TelegramCheckpoint(
            channel=args.channel,
            last_message_id=args.since_message_id,
        )
        if args.since_message_id is not None
        else None
    )
    try:
        result = await adapter.historical(
            args.channel,
            max_messages=args.max_messages,
            start_time=args.start_time,
            end_time=args.end_time,
            checkpoint=checkpoint,
        )
    except (TelegramAPIError, TelegramAuthenticationError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "detail": str(exc)}))
        return 2

    stored = 0
    duplicates = 0
    edges = 0
    try:
        with SessionLocal() as session:
            pipeline = EventPipeline(SocialRepository(session), NLPService())
            for event in result.events:
                processed = pipeline.process(event)
                stored += int(processed.stored)
                duplicates += int(processed.duplicate)
                edges += processed.graph_edges_created
    except SQLAlchemyError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "detail": f"PostgreSQL persistence failed: {type(exc).__name__}",
                    "fetched": result.fetched_count,
                    "normalized": len(result.events),
                }
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": "PASS",
                "fetched": result.fetched_count,
                "normalized": len(result.events),
                "rejected": result.rejected_count,
                "stored": stored,
                "duplicates": duplicates,
                "graph_edges": edges,
                "checkpoint": (
                    result.checkpoint.model_dump(mode="json")
                    if result.checkpoint
                    else None
                ),
            },
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bounded Telegram public-channel history ingestion"
    )
    parser.add_argument("channel", help="Public channel/supergroup username or ID")
    parser.add_argument("--max-messages", type=int, default=20)
    parser.add_argument("--since-message-id", type=int, default=None)
    parser.add_argument("--start-time", type=datetime.fromisoformat, default=None)
    parser.add_argument("--end-time", type=datetime.fromisoformat, default=None)
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
