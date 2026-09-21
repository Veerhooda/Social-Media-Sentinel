import { expect, it } from 'vitest'
import type { NetworkGraphResponse } from '../types/network'
import { positionNetwork } from './network'

it('positions only backend-provided graph nodes deterministically', () => {
  const graph: NetworkGraphResponse = {
    node_count: 2, edge_count: 1, edges: [{ event_id: 'event', source: 'x:a', target: 'x:b', interaction_type: 'mention', weight: 0.5, occurred_at: '2026-09-20T10:00:00Z' }],
    nodes: ['x:a', 'x:b'].map((node_id, index) => ({ node_id, in_degree_centrality: index, out_degree_centrality: 1 - index, betweenness_centrality: 0, closeness_centrality: 0.5, pagerank: 0.5, hub_score: 0.5, authority_score: 0.5, community: index })),
  }
  expect(positionNetwork(graph)).toEqual(positionNetwork(graph))
  expect(positionNetwork(graph).map((node) => node.node_id)).toEqual(['x:a', 'x:b'])
})
