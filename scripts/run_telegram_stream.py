from __future__ import annotations

import argparse
import asyncio
import json

from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.nlp.service import NLPService
from app.pipeline.service import EventPipeline
from app.platforms.telegram.adapter import TelegramAdapter
from app.platforms.telegram.client import TelegramAPIError, TelegramAuthenticationError


async def run(args: argparse.Namespace) -> int:
    if not 1 <= args.duration_seconds <= 300:
        raise ValueError("duration-seconds must be between 1 and 300")
    adapter = TelegramAdapter()
    health = adapter.configuration_health()
    if not health.configured:
        print(json.dumps({"status": "SKIPPED", "detail": health.detail}))
        return 0

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.call_later(args.duration_seconds, stop_event.set)
    stored = 0
    duplicates = 0
    edges = 0
    try:
        with SessionLocal() as session:
            pipeline = EventPipeline(SocialRepository(session), NLPService())

            def process(event):
                nonlocal stored, duplicates, edges
                result = pipeline.process(event)
                stored += int(result.stored)
                duplicates += int(result.duplicate)
                edges += result.graph_edges_created

            stats = await adapter.stream(
                args.channel,
                process,
                stop_event=stop_event,
            )
    except (TelegramAPIError, TelegramAuthenticationError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "detail": str(exc)}))
        return 2

    print(
        json.dumps(
            {
                "status": "PASS" if stats.mapped else "SKIPPED",
                "detail": (
                    None
                    if stats.mapped
                    else "Listener connected and stopped cleanly, but no event arrived"
                ),
                "duration_seconds": args.duration_seconds,
                "received": stats.received,
                "normalized": stats.mapped,
                "rejected": stats.rejected,
                "reconnects": stats.reconnects,
                "stored": stored,
                "duplicates": duplicates,
                "graph_edges": edges,
            },
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Short controlled Telegram public-channel live verification"
    )
    parser.add_argument(
        "--channel",
        action="append",
        required=True,
        help="Public channel/supergroup username or ID; repeat to add another",
    )
    parser.add_argument("--duration-seconds", type=int, default=30)
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
