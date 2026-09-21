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


## Temporal snapshots

`GET /api/network/temporal` splits stored edges into trailing fixed windows
(`15m`, `1h`, `6h`, `24h`) anchored at the latest stored source timestamp.
Chronology uses `created_at` source time; `collected_at` is preserved for
ingestion diagnostics only. Influence deltas (`pagerank increased`,
`betweenness decreased`) are reported only for nodes measured in at least
two windows. Single-measurement nodes never produce emerging-influencer
claims.

## Communities

`GET /api/network/communities` profiles each Louvain community with size,
interaction volume, dominant interaction types, and activity span.
Community identifiers are snapshot-local and are not tracked across
windows.

## Observed cascades

`GET /api/network/cascades` and `GET /api/network/cascades/{cascade_id}`
reconstruct cascades from stored `parent_platform_post_id` chains grouped
under `thread_root_id`. Reported metrics: depth, width, event count,
duration, participants, communities, interaction types, sentiment/emotion
composition from persisted NLP, and a chronological propagation path.
Missing parents are never inferred; such cascades are marked `partially
observable` and only the observed subset is returned. Topic-specific
cascade analysis is explicitly unavailable because per-event topic
assignments are not persisted.

## Terminology

Observed interaction network, structural influence, observed propagation,
temporal graph snapshot, interaction centrality, insufficient relationship
data. No causal influence is claimed. NDLib diffusion simulation is not
integrated; if added later it must stay clearly separated as simulated
versus observed.
