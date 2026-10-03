from __future__ import annotations

import networkx as nx

from app.graph.schemas import CommunityProfile, EdgeRecord


def detect_communities(graph: nx.DiGraph) -> dict[str, int]:
    if graph.number_of_nodes() == 0:
        return {}
    undirected = graph.to_undirected()
    if undirected.number_of_edges() == 0:
        return {str(node): index for index, node in enumerate(undirected.nodes())}
    groups = nx.community.louvain_communities(undirected, weight="weight", seed=42)
    return {str(node): index for index, group in enumerate(groups) for node in group}



def community_profiles(
    edges: list[EdgeRecord],
    communities: dict[str, int],
) -> list[CommunityProfile]:
    """Describe per-snapshot communities: size, volume, types, activity span.

    Community identifiers are snapshot-local. The implementation does not
    preserve identities across windows, so no cross-window identity is claimed.
    """
    from collections import Counter

    members: dict[int, set[str]] = {}
    volumes: dict[int, int] = {}
    type_counts: dict[int, Counter] = {}
    first_seen: dict[int, object] = {}
    last_seen: dict[int, object] = {}
    for node, community in communities.items():
        members.setdefault(community, set()).add(node)
    for edge in edges:
        source = f"{edge.platform}:{edge.source_platform_user_id}"
        target = f"{edge.platform}:{edge.target_platform_user_id}"
        # A cross-community edge is incident to both communities, but it
        # never makes either endpoint a member of the other's community.
        for community in {communities.get(source), communities.get(target)} - {None}:
            volumes[community] = volumes.get(community, 0) + 1
            type_counts.setdefault(community, Counter())[edge.interaction_type] += 1
            if community not in first_seen or edge.occurred_at < first_seen[community]:  # type: ignore[operator]
                first_seen[community] = edge.occurred_at
            if community not in last_seen or edge.occurred_at > last_seen[community]:  # type: ignore[operator]
                last_seen[community] = edge.occurred_at
    profiles = [
        CommunityProfile(
            community_id=community,
            size=len(members.get(community, set())),
            interaction_volume=volumes.get(community, 0),
            dominant_interaction_types=[
                name for name, _ in type_counts.get(community, Counter()).most_common(3)
            ],
            interaction_type_counts=dict(type_counts.get(community, Counter())),
            first_seen_at=first_seen.get(community),  # type: ignore[arg-type]
            last_seen_at=last_seen.get(community),  # type: ignore[arg-type]
        )
        for community in sorted(members)
    ]
    profiles.sort(key=lambda item: item.interaction_volume, reverse=True)
    return profiles
