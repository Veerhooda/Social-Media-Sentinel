import { expect, it } from 'vitest'
import type { NetworkGraphResponse } from '../types/network'
import { buildVisualGraph, communityColor, connectedCore, shortNodeLabel } from './network'

it('builds a deterministic directed network from actual API edges', () => {
  const graph: NetworkGraphResponse = {
    node_count: 2, edge_count: 2, edges: [
      { event_id: 'one', source: 'x:a', target: 'x:b', interaction_type: 'mention', weight: 0.5, occurred_at: '2026-09-20T10:00:00Z' },
      { event_id: 'two', source: 'x:a', target: 'x:b', interaction_type: 'reply', weight: 0.8, occurred_at: '2026-09-20T10:01:00Z' },
    ],
    nodes: ['x:a', 'x:b'].map((node_id, index) => ({ node_id, in_degree_centrality: index, out_degree_centrality: 1 - index, betweenness_centrality: 0, closeness_centrality: 0.5, pagerank: 0.5, hub_score: 0.5, authority_score: 0.5, community: index })),
  }
  const first = buildVisualGraph(graph)
  const second = buildVisualGraph(graph)
  expect(first.nodes()).toEqual(['x:a', 'x:b'])
  expect(first.size).toBe(1)
  expect(first.getEdgeAttribute(first.edge('x:a', 'x:b')!, 'count')).toBe(2)
  expect(first.getEdgeAttribute(first.edge('x:a', 'x:b')!, 'weight')).toBe(1.3)
  expect(first.getNodeAttribute('x:a', 'x')).toBe(second.getNodeAttribute('x:a', 'x'))
  expect(first.getNodeAttribute('x:a', 'y')).toBe(second.getNodeAttribute('x:a', 'y'))
  expect(communityColor(0)).not.toBe(communityColor(1))
  expect(shortNodeLabel('x:a')).toBe('a')
})

it('keeps the connected core tied to visible observed edges', () => {
  const graph: NetworkGraphResponse = {
    node_count: 3, edge_count: 1,
    nodes: ['x:a', 'x:b', 'x:isolated'].map((node_id) => ({ node_id, in_degree_centrality: 0, out_degree_centrality: 0, betweenness_centrality: 0, closeness_centrality: 0, pagerank: 0.1, hub_score: 0, authority_score: 0, community: 0 })),
    edges: [{ event_id: 'one', source: 'x:a', target: 'x:b', interaction_type: 'reply', weight: 0.8, occurred_at: '2026-09-20T10:00:00Z' }],
  }
  expect(connectedCore(graph).nodes.map((node) => node.node_id)).toEqual(['x:a', 'x:b'])
  expect(connectedCore(graph, 1).edge_count).toBe(0)
})
