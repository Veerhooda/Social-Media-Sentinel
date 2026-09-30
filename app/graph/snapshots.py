"""Temporal graph snapshots from stored source timestamps.

Analytical chronology always uses ``occurred_at`` (source ``created_at``).
Windows are bounded presets anchored at the latest stored edge so snapshots
are reproducible and never random.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.graph.builder import GraphBuilder
from app.graph.metrics import calculate_network_metrics
from app.graph.schemas import EdgeRecord, InfluenceDelta, TemporalSnapshot

WINDOW_PRESETS: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
}

TRACKED_METRICS = ("pagerank", "betweenness_centrality")


def build_snapshots(
    edges: list[EdgeRecord],
    *,
    window: str = "1h",
    count: int = 6,
    include_metrics: bool = False,
) -> tuple[list[TemporalSnapshot], datetime | None]:
    """Split stored edges into trailing fixed windows ending at the latest edge."""
    if window not in WINDOW_PRESETS:
        raise ValueError(f"unsupported window {window!r}; expected one of {sorted(WINDOW_PRESETS)}")
    if count < 1:
        raise ValueError("window count must be positive")
    if not edges:
        return [], None
    step = WINDOW_PRESETS[window]
    latest = max(edge.occurred_at for edge in edges).astimezone(UTC)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    elapsed = latest - epoch
    step_count = elapsed // step
    # Windows are half open, so use the first boundary strictly after the
    # latest event. The prior implementation dropped the newest edge.
    anchored_at = epoch + (step_count + 1) * step
    snapshots: list[TemporalSnapshot] = []
    for index in range(count):
        window_end = anchored_at - step * index
        window_start = window_end - step
        selected = [edge for edge in edges if window_start <= edge.occurred_at < window_end]
        summary = calculate_network_metrics(GraphBuilder.build_graph(selected))
        snapshots.append(
            TemporalSnapshot(
                window_start=window_start,
                window_end=window_end,
                label=f"T-{index * step.total_seconds() / 3600:.2g}h",
                nodes=summary.nodes,
                edges=summary.edges,
                density=summary.density,
                communities=summary.communities,
                summary=summary if include_metrics else None,
            )
        )
    snapshots.reverse()
    return snapshots, anchored_at


def influence_changes(snapshots: list[TemporalSnapshot]) -> list[InfluenceDelta]:
    """Compare per-node metrics across snapshots with actual measurements only.

    A direction is reported only when a node was measured in at least two
    windows. Single-measurement nodes never produce an "emerging" claim.
    """
    series: dict[tuple[str, str], list[float]] = {}
    for snapshot in snapshots:
        if snapshot.summary is None:
            continue
        for metric in snapshot.summary.metrics:
            for name in TRACKED_METRICS:
                series.setdefault((metric.node_id, name), []).append(getattr(metric, name))
    deltas: list[InfluenceDelta] = []
    for (node_id, name), values in series.items():
        if len(values) < 2:
            continue
        change = values[-1] - values[0]
        direction = (
            f"{name} increased" if change > 0 else f"{name} decreased" if change < 0 else f"{name} unchanged"
        )
        deltas.append(
            InfluenceDelta(
                node_id=node_id,
                metric=name,
                first_value=values[0],
                last_value=values[-1],
                change=change,
                direction=direction,
                windows_measured=len(values),
            )
        )
    deltas.sort(key=lambda item: abs(item.change), reverse=True)
    return deltas
