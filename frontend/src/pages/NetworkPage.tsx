import { GitBranch, Network, Orbit, UsersRound } from 'lucide-react'
import { useMemo, useState } from 'react'
import { MetricCard } from '../components/MetricCard'
import { AccountAvatar } from '../components/AccountAvatar'
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
import { communityColor, nodeLabel, profileLink } from '../utils/network'

const WINDOWS = ['15m', '1h', '6h', '24h'] as const

export function NetworkPage() {
  const [summary, graph] = useNetwork()
  const [selected, setSelected] = useState<string | null>(null)
  const [focusedCommunity, setFocusedCommunity] = useState<number | null>(null)
  const [window, setWindow] = useState<string>('1h')
  const [cascadeId, setCascadeId] = useState<string | null>(null)
  const temporal = useNetworkTemporal(window)
  const influence = useNetworkInfluence()
  const communities = useNetworkCommunities()
  const cascades = useNetworkCascades()
  const cascade = useNetworkCascade(cascadeId)
  const selectedNode = graph.data?.nodes.find((node) => node.node_id === selected)
  const mappedCoverage = communities.data?.coverage
  const top = useMemo(() => [...(graph.data?.nodes ?? [])]
    .filter((node) => node.profile?.status === 'stored_profile')
    .sort((left, right) => right.pagerank - left.pagerank)
    .slice(0, 8), [graph.data])
  const relationships = useMemo(() => Object.entries((graph.data?.edges ?? []).reduce<Record<string, number>>((counts, edge) => {
    counts[edge.interaction_type] = (counts[edge.interaction_type] ?? 0) + 1
    return counts
  }, {})).sort(([, left], [, right]) => right - left), [graph.data])
  if (summary.isLoading || graph.isLoading) return <LoadingState label="Loading interaction graph…" />
  if (summary.error || graph.error) return <ErrorState error={summary.error ?? graph.error} />
  return (
    <div className="page-stack">
      <PageHeader title="Interaction map" subtitle="Explore observed replies, mentions, quotes, reposts and forwards. This maps interaction structure—not a follower network or causal influence." />
      <div className="metric-grid metric-grid--four"><MetricCard label="Nodes" value={formatNumber(summary.data?.summary.nodes ?? 0)} detail="observed accounts" icon={UsersRound} tone="blue" /><MetricCard label="Edges" value={formatNumber(summary.data?.summary.edges ?? 0)} detail="aggregated interactions" icon={GitBranch} /><MetricCard label="Communities" value={summary.data?.summary.communities ?? 0} detail="Louvain partition" icon={Orbit} tone="purple" /><MetricCard label="Density" value={(summary.data?.summary.density ?? 0).toFixed(4)} detail="directed graph density" icon={Network} tone="green" /></div>
      {mappedCoverage && <section className="network-summary-strip" aria-label="Audience map coverage">
        <strong>{formatNumber(mappedCoverage.stored_profiles)} / {formatNumber(mappedCoverage.total_nodes)} mapped accounts have stored profiles</strong>
        <span>{formatNumber(mappedCoverage.referenced_only)} referenced only · {formatNumber(mappedCoverage.avatar_available)} avatar URLs · {formatNumber(mappedCoverage.demographic_records)} aggregate records</span>
      </section>}
      <div className="network-layout">
        <Panel title="Conversation topology" subtitle="Recent-edge sample · directed stored interactions · colors and node size recalculated for this loaded graph" className="network-layout__graph"><NetworkGraph graph={graph.data!} onSelect={setSelected} selected={selected} focusedCommunity={focusedCommunity} /><div className="relationship-legend">{relationships.map(([type, count]) => <span key={type}><i />{type} <b>{count}</b></span>)}</div></Panel>
        <Panel title={selectedNode ? 'Selected account' : 'Mapped profiles'} subtitle={selectedNode ? selectedNode.node_id : 'Stored public profiles · ranked by PageRank within the loaded graph'} className="network-layout__side">
          {selectedNode ? <><button type="button" className="network-selection-back" onClick={() => setSelected(null)}>← Back to ranking</button><div className="network-account"><AccountAvatar node={selectedNode} size={54} /><div><strong>{nodeLabel(selectedNode)}</strong><span>{selectedNode.profile?.status === 'stored_profile' ? selectedNode.profile.username ? `@${selectedNode.profile.username}` : 'Stored public profile' : 'Referenced only · profile not collected'}</span>{profileLink(selectedNode) && <a href={profileLink(selectedNode)!} target="_blank" rel="noopener noreferrer">View public profile ↗</a>}</div></div><dl className="detail-list"><dt>Community</dt><dd>{selectedNode.community ?? 'Unknown'}</dd><dt>PageRank</dt><dd>{selectedNode.pagerank.toFixed(5)}</dd><dt>Authority</dt><dd>{selectedNode.authority_score.toFixed(5)}</dd><dt>Hub</dt><dd>{selectedNode.hub_score.toFixed(5)}</dd><dt>Betweenness</dt><dd>{selectedNode.betweenness_centrality.toFixed(5)}</dd></dl><div className="network-relationships"><h3>Observed relationships</h3>{graph.data!.edges.filter((edge) => edge.source === selected || edge.target === selected).slice(0, 10).map((edge) => <p key={[edge.event_id, edge.source, edge.target, edge.interaction_type].join(':')}><span>{edge.source === selected ? 'Outgoing' : 'Incoming'} · {edge.interaction_type}</span><strong>{nodeLabel(graph.data!.nodes.find((node) => node.node_id === (edge.source === selected ? edge.target : edge.source)) ?? selectedNode)}</strong><small>{formatDateTime(edge.occurred_at)}</small></p>)}</div></> : <div className="ranking-list">{top.map((node, index) => <button type="button" key={node.node_id} onClick={() => setSelected(node.node_id)}><b>{index + 1}</b><AccountAvatar node={node} size={32} /><span>{nodeLabel(node)}<small>{node.profile?.status === 'stored_profile' ? 'Stored public profile' : 'Referenced only'} · community {node.community ?? '—'}</small></span><em>{node.pagerank.toFixed(4)}</em></button>)}</div>}
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
        <Panel title="Interaction Centrality" subtitle="Whole stored graph · structural rank may differ from sampled community profiles" className="span-6">
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
        <Panel title="Communities" subtitle="Recent-edge sample · select a community to highlight its mapped accounts" className="span-6">
          {communities.isLoading ? <LoadingState label="Loading communities…" /> : communities.error ? <ErrorState error={communities.error} /> : (communities.data?.communities.length ?? 0) === 0 ? (
            <EmptyState title="No communities" detail="No interaction relationships available for this window." />
          ) : (
            <div className="community-list">
              {communities.data!.communities.slice(0, 8).map((community) => (
                <article key={community.community_id} className="community-card" style={{ borderLeftColor: communityColor(community.community_id) }}>
                  <header><button type="button" aria-pressed={focusedCommunity === community.community_id} onClick={() => { setSelected(null); const next = focusedCommunity === community.community_id ? null : community.community_id; setFocusedCommunity(next); if (next !== null) document.getElementById('audience-network-map')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }) }}>Community {community.community_id}{focusedCommunity === community.community_id ? ' · showing' : ' · show on map'}</button><span>{community.size} accounts · {community.interaction_volume} incident interactions</span></header>
                  <p>{community.stored_profiles} stored profiles · {community.referenced_only} referenced only</p>
                  <p>Interaction types: {community.dominant_interaction_types.join(', ') || 'unknown'}</p>
                  <div className="community-audience">
                    {(['language', 'geography', 'profession'] as const).map((dimension) => {
                      const signal = community.audience?.[dimension]
                      const top = signal && Object.entries(signal.distribution).sort((a, b) => b[1] - a[1])[0]
                      return <span key={dimension}><b>{dimension}</b> {signal?.status === 'AVAILABLE' && top ? `${top[0]} · ${top[1]}/${community.size}` : 'Insufficient data'}<small>{signal?.known ?? 0} known · {signal?.unknown ?? community.size} unknown{signal?.suppressed ? ` · ${signal.suppressed} withheld` : ''}</small></span>
                    })}
                  </div>
                </article>
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
