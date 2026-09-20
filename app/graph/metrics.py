from __future__ import annotations

import networkx as nx

from app.graph.communities import detect_communities
from app.graph.schemas import NetworkSummary, NodeMetrics


def calculate_network_metrics(graph: nx.DiGraph) -> NetworkSummary:
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    if node_count == 0:
        return NetworkSummary(nodes=0, edges=0, density=0.0, communities=0, metrics=[])

    in_degree = nx.in_degree_centrality(graph)
    out_degree = nx.out_degree_centrality(graph)
    betweenness = nx.betweenness_centrality(graph, weight="weight", normalized=True)
    closeness = nx.closeness_centrality(graph)
    pagerank = nx.pagerank(graph, weight="weight")
    if edge_count:
        try:
            hubs, authorities = nx.hits(graph, max_iter=1000, normalized=True)
        except nx.PowerIterationFailedConvergence:
            hubs = {node: 0.0 for node in graph}
            authorities = {node: 0.0 for node in graph}
    else:
        hubs = {node: 0.0 for node in graph}
        authorities = {node: 0.0 for node in graph}
    communities = detect_communities(graph)

    metrics = [
        NodeMetrics(
            node_id=str(node),
            in_degree_centrality=float(in_degree.get(node, 0.0)),
            out_degree_centrality=float(out_degree.get(node, 0.0)),
            betweenness_centrality=float(betweenness.get(node, 0.0)),
            closeness_centrality=float(closeness.get(node, 0.0)),
            pagerank=float(pagerank.get(node, 0.0)),
            hub_score=float(hubs.get(node, 0.0)),
            authority_score=float(authorities.get(node, 0.0)),
            community=communities.get(str(node)),
        )
        for node in graph.nodes()
    ]
    metrics.sort(key=lambda item: item.pagerank, reverse=True)
    return NetworkSummary(
        nodes=node_count,
        edges=edge_count,
        density=float(nx.density(graph)),
        communities=len(set(communities.values())),
        metrics=metrics,
    )

