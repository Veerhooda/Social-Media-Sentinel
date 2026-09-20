from __future__ import annotations

import networkx as nx


def detect_communities(graph: nx.DiGraph) -> dict[str, int]:
    if graph.number_of_nodes() == 0:
        return {}
    undirected = graph.to_undirected()
    if undirected.number_of_edges() == 0:
        return {str(node): index for index, node in enumerate(undirected.nodes())}
    groups = nx.community.louvain_communities(undirected, weight="weight", seed=42)
    return {str(node): index for index, group in enumerate(groups) for node in group}

