import { GitBranch, Network, Orbit, UsersRound } from 'lucide-react'
import { useMemo, useState } from 'react'
import { MetricCard } from '../components/MetricCard'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import {
  useNetwork,
  useNetworkCascade,
  useNetworkCascades,
  useNetworkCommunities,
  useNetworkInfluence,
  useNetworkTemporal,
} from '../hooks/useApiQueries'
import { NetworkGraph } from '../network/NetworkGraph'
import { formatDateTime, formatDuration, formatNumber } from '../utils/format'

const WINDOWS = ['15m', '1h', '6h', '24h'] as const

export function NetworkPage() {
  const [summary, graph] = useNetwork()
  const [selected, setSelected] = useState<string | null>(null)
  const [window, setWindow] = useState<string>('1h')
  const [cascadeId, setCascadeId] = useState<string | null>(null)
  const temporal = useNetworkTemporal(window)
  const influence = useNetworkInfluence()
  const communities = useNetworkCommunities()
  const cascades = useNetworkCascades()
  const cascade = useNetworkCascade(cascadeId)
  const selectedNode = graph.data?.nodes.find((node) => node.node_id === selected)
  const top = useMemo(() => [...(summary.data?.summary.metrics ?? [])].sort((left, right) => right.pagerank - left.pagerank).slice(0, 8), [summary.data])
  const relationships = useMemo(() => Object.entries((graph.data?.edges ?? []).reduce<Record<string, number>>((counts, edge) => {
    counts[edge.interaction_type] = (counts[edge.interaction_type] ?? 0) + 1
    return counts
  }, {})).sort(([, left], [, right]) => right - left), [graph.data])
  if (summary.isLoading || graph.isLoading) return <LoadingState label="Loading interaction graph…" />
  if (summary.error || graph.error) return <ErrorState error={summary.error ?? graph.error} />
  return (
    <div className="page-stack">
      <PageHeader title="Network Analysis" subtitle="Observed interaction network from replies, mentions, quotes, reposts and forwards—structural influence only, never causal claims." />
      <div className="metric-grid metric-grid--four"><MetricCard label="Nodes" value={formatNumber(summary.data?.summary.nodes ?? 0)} detail="observed accounts" icon={UsersRound} tone="blue" /><MetricCard label="Edges" value={formatNumber(summary.data?.summary.edges ?? 0)} detail="aggregated interactions" icon={GitBranch} /><MetricCard label="Communities" value={summary.data?.summary.communities ?? 0} detail="Louvain partition" icon={Orbit} tone="purple" /><MetricCard label="Density" value={(summary.data?.summary.density ?? 0).toFixed(4)} detail="directed graph density" icon={Network} tone="green" /></div>
      <div className="network-layout">
        <Panel title="Interaction Network" subtitle="Actual collected relationships · node size follows PageRank" className="network-layout__graph"><NetworkGraph graph={graph.data!} onSelect={setSelected} /><div className="relationship-legend">{relationships.map(([type, count]) => <span key={type}><i />{type} <b>{count}</b></span>)}</div></Panel>
        <Panel title={selectedNode ? 'Selected Node' : 'Top Influence'} subtitle={selectedNode ? selectedNode.node_id : 'Structural metrics, not causal influence'} className="network-layout__side">
          {selectedNode ? <dl className="detail-list"><dt>Community</dt><dd>{selectedNode.community ?? 'Unknown'}</dd><dt>PageRank</dt><dd>{selectedNode.pagerank.toFixed(5)}</dd><dt>Authority</dt><dd>{selectedNode.authority_score.toFixed(5)}</dd><dt>Hub</dt><dd>{selectedNode.hub_score.toFixed(5)}</dd><dt>Betweenness</dt><dd>{selectedNode.betweenness_centrality.toFixed(5)}</dd></dl> : <div className="ranking-list">{top.map((node, index) => <button type="button" key={node.node_id} onClick={() => setSelected(node.node_id)}><b>{index + 1}</b><span>{node.node_id}</span><em>{node.pagerank.toFixed(4)}</em></button>)}</div>}
        </Panel>
      </div>

      <Panel
        title="Temporal Network"
        subtitle="Snapshots use source timestamps; chronology is analytical, not ingestion order."
        action={
          <div className="table-toolbar" role="group" aria-label="Snapshot window">
            {WINDOWS.map((option) => (
              <button key={option} type="button" className={window === option ? 'is-active' : ''} onClick={() => setWindow(option)}>{option}</button>
            ))}
          </div>
        }
      >
        {temporal.isLoading ? <LoadingState label="Loading temporal snapshots…" /> : temporal.error ? <ErrorState error={temporal.error} /> : (temporal.data?.snapshots.filter((s) => s.edges).length ?? 0) === 0 ? (
          <EmptyState title="No interaction relationships" detail="No interaction relationships available for this window." />
        ) : (
          <>
            <div className="data-table"><div className="data-table__header temporal-columns"><span>Window end</span><span>Nodes</span><span>Edges</span><span>Communities</span><span>Density</span></div>
              {temporal.data!.snapshots.map((snapshot) => (
                <div className="data-table__row temporal-columns" key={snapshot.window_end}>
                  <time>{formatDateTime(snapshot.window_end)}</time><b>{formatNumber(snapshot.nodes)}</b><span>{formatNumber(snapshot.edges)}</span><span>{snapshot.communities}</span><span>{snapshot.density.toFixed(4)}</span>
                </div>
              ))}
            </div>
            <p className="muted-copy">{temporal.data!.detail}</p>
            {(temporal.data?.influence_changes.length ?? 0) > 0 && (
              <div className="insight-list">
                {temporal.data!.influence_changes.slice(0, 6).map((delta) => (
                  <p key={`${delta.node_id}-${delta.metric}`}><b>{delta.node_id}</b><span>{delta.direction} ({delta.first_value.toFixed(4)} → {delta.last_value.toFixed(4)} across {delta.windows_measured} windows)</span></p>
                ))}
              </div>
            )}
          </>
        )}
      </Panel>

      <div className="dashboard-grid">
        <Panel title="Interaction Centrality" subtitle={influence.data?.detail ?? 'Ranked structural metrics with graph context.'} className="span-6">
          {influence.isLoading ? <LoadingState label="Loading influence table…" /> : influence.error ? <ErrorState error={influence.error} /> : (influence.data?.items.length ?? 0) === 0 ? (
            <EmptyState title="Insufficient relationship data" detail="No ranked nodes for this selection." />
          ) : (
            <div className="data-table"><div className="data-table__header influence-columns"><span>Node</span><span>PageRank</span><span>Betweenness</span><span>Authority</span></div>
              {influence.data!.items.map((node) => (
                <div className="data-table__row influence-columns" key={node.node_id}><span>{node.node_id}</span><b>{node.pagerank.toFixed(4)}</b><span>{node.betweenness_centrality.toFixed(4)}</span><span>{node.authority_score.toFixed(4)}</span></div>
              ))}
            </div>
          )}
        </Panel>
        <Panel title="Communities" subtitle={communities.data?.detail ?? 'Snapshot-local identifiers; not tracked across windows.'} className="span-6">
          {communities.isLoading ? <LoadingState label="Loading communities…" /> : communities.error ? <ErrorState error={communities.error} /> : (communities.data?.communities.length ?? 0) === 0 ? (
            <EmptyState title="No communities" detail="No interaction relationships available for this window." />
          ) : (
            <div className="distribution-list">
              {communities.data!.communities.slice(0, 8).map((community) => (
                <div key={community.community_id} title={`${community.interaction_volume} interactions · ${community.dominant_interaction_types.join(', ') || 'no typed edges'}`}>
                  <span>Community {community.community_id}</span>
                  <div><i style={{ width: `${Math.max(2, (community.size / Math.max(1, communities.data!.communities[0].size)) * 100)}%` }} /></div>
                  <b>{community.size}</b>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Observed Cascades"
        subtitle="Reconstructed from stored parent relationships only. Missing parents are never inferred."
        action={cascades.data ? <StatusBadge status={cascades.data.count ? 'AVAILABLE' : 'INSUFFICIENT_DATA'} /> : undefined}
      >
        {cascades.isLoading ? <LoadingState label="Loading observed cascades…" /> : cascades.error ? <ErrorState error={cascades.error} /> : (cascades.data?.count ?? 0) === 0 ? (
          <EmptyState title="No observable cascade" detail="No observable cascade reconstructed." />
        ) : (
          <>
            <div className="data-table"><div className="data-table__header cascade-columns"><span>Cascade</span><span>Events</span><span>Depth</span><span>Width</span><span>Duration</span><span>Provenance</span><span /></div>
              {cascades.data!.cascades.slice(0, 10).map((item) => (
                <div className="data-table__row cascade-columns" key={item.cascade_id}>
                  <span>{item.cascade_id}</span><b>{item.event_count}</b><span>{item.depth}</span><span>{item.width}</span><span>{item.duration_seconds != null ? formatDuration(item.duration_seconds) : '—'}</span><span>{item.provenance}</span>
                  <button type="button" onClick={() => setCascadeId(item.cascade_id)}>Open</button>
                </div>
              ))}
            </div>
            <p className="muted-copy">{cascades.data!.detail} Largest: {cascades.data!.largest_cascade_id} · max depth {cascades.data!.max_depth}.</p>
          </>
        )}
      </Panel>

      {cascadeId && (
        <Panel title={`Propagation path · ${cascadeId}`} subtitle="Chronological observed steps with community and NLP signals where available.">
          {cascade.isLoading ? <LoadingState label="Loading propagation path…" /> : cascade.error ? <ErrorState error={cascade.error} /> : !cascade.data ? (
            <EmptyState title="No observable cascade" detail="Propagation path is partially observable." />
          ) : (
            <>
              <div className="insight-list">
                <p><b>Provenance</b><span>{cascade.data.provenance}{cascade.data.provenance !== 'observed' ? ' — propagation path shows the observed subset only.' : ''}</span></p>
                <p><b>Sentiment</b><span>{Object.keys(cascade.data.sentiment_counts).length ? `Observed composition across cascade events: ${Object.entries(cascade.data.sentiment_counts).map(([label, count]) => `${label} ${count}`).join(' · ')}` : 'No NLP results attached to these events.'}</span></p>
                <p><b>Topics</b><span>Unavailable — per-event topic assignments are not persisted.</span></p>
              </div>
              <div className="propagation-path">
                {cascade.data.propagation_path.map((step) => (
                  <div className="propagation-path__step" key={step.event_id}>
                    <b>#{step.depth} {step.node_id}</b>
                    <span>{step.interaction_type} · {formatDateTime(step.occurred_at)}</span>
                    <span>community {step.community ?? 'unknown'}{step.sentiment ? ` · ${step.sentiment}` : ''}{step.emotion ? ` · ${step.emotion}` : ''}{step.is_ironic ? ' · ironic' : ''}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Panel>
      )}

      <Panel title="Interpretation" subtitle="Responsible network language"><p className="muted-copy">{summary.data?.summary.interpretation}</p></Panel>
    </div>
  )
}
