from __future__ import annotations

import importlib
import os
import platform
import sys
from collections.abc import Callable


def report(status: str, name: str, detail: str) -> None:
    print(f"{status:<11} {name:<24} {detail}")


def check(name: str, operation: Callable[[], str]) -> bool:
    try:
        report("PASS", name, operation())
        return True
    except Exception as exc:
        report("FAIL", name, f"{type(exc).__name__}: {exc}")
        return False


def import_check(module_name: str) -> str:
    module = importlib.import_module(module_name)
    return str(getattr(module, "__version__", "imported"))


def database_check() -> str:
    from sqlalchemy import create_engine, text

    from app.core.config import get_settings

    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    with engine.connect() as connection:
        value = connection.execute(text("SELECT version()"))
        return str(value.scalar_one()).split(",")[0]


def graph_check() -> str:
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_edge("x:a", "x:b", weight=1.0)
    ranks = nx.pagerank(graph, weight="weight")
    if set(ranks) != {"x:a", "x:b"}:
        raise RuntimeError("unexpected PageRank result")
    return f"PageRank calculated for {len(ranks)} nodes"


def main() -> int:
    failures = 0
    if sys.version_info[:2] == (3, 13):
        report("PASS", "Python", platform.python_version())
    else:
        report("FAIL", "Python", f"expected 3.13, got {platform.python_version()}")
        failures += 1

    for label, module in [
        ("Pydantic", "pydantic"),
        ("FastAPI", "fastapi"),
        ("Uvicorn", "uvicorn"),
        ("Tweepy", "tweepy"),
        ("Transformers", "transformers"),
        ("PyTorch", "torch"),
        ("NetworkX", "networkx"),
        ("SQLAlchemy", "sqlalchemy"),
        ("Psycopg", "psycopg"),
        ("BERTrend", "bertrend"),
    ]:
        failures += not check(label, lambda module=module: import_check(module))

    failures += not check("PostgreSQL", database_check)
    failures += not check("NetworkX algorithm", graph_check)

    if os.getenv("X_BEARER_TOKEN"):
        report("PASS", "X credentials", "bearer token configured; no live request made")
    else:
        report("SKIPPED", "X credentials", "X_BEARER_TOKEN is not configured")

    report(
        "SKIPPED",
        "Transformer weights",
        "run scripts/model_smoke_test.py for controlled checkpoint download/inference",
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

