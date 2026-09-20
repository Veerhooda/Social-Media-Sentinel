from __future__ import annotations

from datetime import datetime

from app.graph.builder import GraphBuilder
from app.graph.metrics import calculate_network_metrics
from app.graph.schemas import EdgeRecord, NetworkSummary


def network_summary_for_window(
    edges: list[EdgeRecord], *, start: datetime | None = None, end: datetime | None = None
) -> NetworkSummary:
    selected = [
        edge
        for edge in edges
        if (start is None or edge.occurred_at >= start) and (end is None or edge.occurred_at < end)
    ]
    return calculate_network_metrics(GraphBuilder.build_graph(selected))

