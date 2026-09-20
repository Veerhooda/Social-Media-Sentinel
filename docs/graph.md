# Graph Analytics

Graphs are derived only from normalized collected events.

## Edge extraction

| Interaction | Source | Target | Default weight |
|---|---|---|---:|
| reply | replying author | parent author | 0.8 |
| mention | mentioning author | mentioned user | 0.5 |
| repost | reposting author | original author | 1.0 |
| quote | quoting author | quoted author | 1.0 |

The defaults are configurable engineering weights, not empirically established influence probabilities. Multiple persisted relationships between the same ordered pair are aggregated into one weighted NetworkX edge while retaining interaction-type metadata.

## Metrics

The service calculates:

- in/out degree centrality
- betweenness centrality
- closeness centrality
- PageRank
- HITS hub/authority scores
- Louvain communities on the undirected projection

Results describe structural interaction patterns in collected data. They are not causal claims about real-world influence.

No follower network is claimed or constructed because follower-edge availability has not been verified for the configured X access.

