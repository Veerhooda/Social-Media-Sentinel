import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { NetworkPage } from './NetworkPage'

afterEach(() => vi.unstubAllGlobals())

const summary = {
  summary: {
    nodes: 4,
    edges: 3,
    density: 0.25,
    communities: 1,
    metrics: [
      {
        node_id: 'x:alice', in_degree_centrality: 0, out_degree_centrality: 0.3,
        betweenness_centrality: 0.1, closeness_centrality: 0.4, pagerank: 0.3,
        hub_score: 0.2, authority_score: 0.1, community: 0,
      },
    ],
    interpretation: 'Structural metrics only.',
  },
}
const graph = { nodes: summary.summary.metrics, edges: [], node_count: 1, edge_count: 0 }
const temporal = {
  window: '1h', window_count: 2, anchored_at: '2026-09-20T12:00:00Z',
  snapshots: [
    { window_start: '2026-09-20T10:00:00Z', window_end: '2026-09-20T11:00:00Z', label: 'T-1h', nodes: 2, edges: 1, density: 0.5, communities: 1 },
    { window_start: '2026-09-20T11:00:00Z', window_end: '2026-09-20T12:00:00Z', label: 'T-0h', nodes: 3, edges: 2, density: 0.33, communities: 1 },
  ],
  influence_changes: [
    { node_id: 'x:alice', metric: 'pagerank', first_value: 0.2, last_value: 0.3, change: 0.1, direction: 'pagerank increased', windows_measured: 2 },
  ],
  detail: 'Observed temporal snapshots over 2 populated windows.',
}
const influence = {
  metric: 'pagerank', window_start: null, window_end: null, nodes: 4, edges: 3,
  items: [summary.summary.metrics[0]], detail: 'Ranked by observed interaction structure.',
}
const communities = {
  window_start: null, window_end: null,
  communities: [
    { community_id: 0, size: 4, interaction_volume: 3, dominant_interaction_types: ['reply'], interaction_type_counts: { reply: 3 }, first_seen_at: null, last_seen_at: null },
  ],
  detail: 'Snapshot-local identifiers.',
}
const cascades = {
  cascades: [
    {
      cascade_id: 'x:root-1', platform: 'x', root_platform_post_id: 'root-1', event_count: 3,
      depth: 2, width: 2, duration_seconds: 600, participant_count: 3, community_count: 1,
      interaction_types: ['reply'], started_at: null, last_activity_at: null, provenance: 'observed',
    },
  ],
  count: 1, largest_cascade_id: 'x:root-1', max_depth: 2, detail: '1 observed cascades.',
}

function renderPage() {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      const body = url.includes('/network/temporal')
        ? temporal
        : url.includes('/network/influence')
          ? influence
          : url.includes('/network/communities')
            ? communities
            : url.includes('/network/cascades')
              ? cascades
              : url.includes('/network/graph')
                ? graph
                : summary
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <NetworkPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

it('renders temporal snapshots, influence, communities and observed cascades', async () => {
  renderPage()
  expect(await screen.findByText('Temporal Network')).toBeInTheDocument()
  expect(screen.getByText('Interaction Centrality')).toBeInTheDocument()
  expect(screen.getAllByText('Communities').length).toBeGreaterThan(0)
  expect(screen.getByText('Observed Cascades')).toBeInTheDocument()
  expect(screen.getByText('x:root-1')).toBeInTheDocument()
  expect(screen.getByText(/pagerank increased/)).toBeInTheDocument()
  expect(screen.queryByText(/Most powerful users/i)).not.toBeInTheDocument()
})
