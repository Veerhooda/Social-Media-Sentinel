from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from app.graph.schemas import EdgeRecord
from app.models.events import CanonicalEvent


@dataclass(frozen=True)
class EdgeWeights:
    repost: float = 1.0
    quote: float = 1.0
    mention: float = 0.5
    reply: float = 0.8
    forward: float = 1.0


class GraphBuilder:
    def __init__(self, weights: EdgeWeights | None = None):
        self.weights = weights or EdgeWeights()

    def edges_from_event(self, event: CanonicalEvent) -> list[EdgeRecord]:
        source = event.author.platform_user_id
        targets: list[tuple[str, str, float]] = []
        relationships = event.relationships
        if relationships.parent_author_id:
            targets.append((relationships.parent_author_id, "reply", self.weights.reply))
        if relationships.repost_of_author_id:
            targets.append((relationships.repost_of_author_id, "repost", self.weights.repost))
        if relationships.quote_of_author_id:
            targets.append((relationships.quote_of_author_id, "quote", self.weights.quote))
        if relationships.forwarded_from_id:
            targets.append((relationships.forwarded_from_id, "forward", self.weights.forward))

        if event.source_metadata.get("mention_relationships_verified", True):
            mention_ids = event.source_metadata.get("mention_ids") or []
            mention_targets = [str(item) for item in mention_ids]
            if not mention_targets:
                mention_targets = [f"username:{username.lower()}" for username in event.content.mentions]
            targets.extend((target, "mention", self.weights.mention) for target in mention_targets)

        unique: dict[tuple[str, str], EdgeRecord] = {}
        for target, kind, weight in targets:
            if not target or target == source:
                continue
            key = (target, kind)
            unique[key] = EdgeRecord(
                event_id=event.event_id,
                platform=event.platform.value,
                source_platform_user_id=source,
                target_platform_user_id=target,
                interaction_type=kind,
                weight=weight,
                occurred_at=event.created_at,
            )
        return list(unique.values())

    @staticmethod
    def build_graph(edges: list[EdgeRecord]) -> nx.DiGraph:
        graph = nx.DiGraph()
        for edge in edges:
            source = f"{edge.platform}:{edge.source_platform_user_id}"
            target = f"{edge.platform}:{edge.target_platform_user_id}"
            if graph.has_edge(source, target):
                graph[source][target]["weight"] += edge.weight
                graph[source][target]["count"] += 1
                graph[source][target]["interaction_types"].add(edge.interaction_type)
            else:
                graph.add_edge(
                    source,
                    target,
                    weight=edge.weight,
                    count=1,
                    interaction_types={edge.interaction_type},
                )
        return graph
