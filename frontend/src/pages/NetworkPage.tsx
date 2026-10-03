import { ExternalLink, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { AccountAvatar } from '../components/AccountAvatar'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { platformLabel } from '../utils/platform'
import { Segmented } from '../components/Segmented'
import { Stat, Stats } from '../components/Stat'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import {
  useNetwork,
  useNetworkCascade,
  useNetworkCascades,
  useNetworkCommunities,
  useNetworkInfluence,
  useNetworkTemporal,
} from '../hooks/useApiQueries'
import { NetworkGraph } from '../network/NetworkGraph'
import { formatDuration, formatNumber, formatShortTime, sentenceCase } from '../utils/format'
import { communityColor, nodeLabel, profileLink, shortNodeLabel } from '../utils/network'

const WINDOWS = ['15m', '1h', '6h', '24h'] as const

export function NetworkPage() {
  const [summary, graph] = useNetwork()
  const [selected, setSelected] = useState<string | null>(null)
  const [community, setCommunity] = useState<number | null>(null)
  const [window, setWindow] = useState<(typeof WINDOWS)[number]>('24h')
  const [cascadeId, setCascadeId] = useState<string | null>(null)
  const temporal = useNetworkTemporal(window)
  const influence = useNetworkInfluence()
  const communities = useNetworkCommunities()
  const cascades = useNetworkCascades()
  const cascade = useNetworkCascade(cascadeId)

  const nodes = useMemo(() => graph.data?.nodes ?? [], [graph.data])
  const selectedNode = nodes.find((node) => node.node_id === selected)
  const ranking = useMemo(() => [...nodes].sort((a, b) => b.pagerank - a.pagerank).slice(0, 12), [nodes])
  const relationships = useMemo(() => Object.entries((graph.data?.edges ?? []).reduce<Record<string, number>>((counts, edge) => {
    counts[edge.interaction_type] = (counts[edge.interaction_type] ?? 0) + 1
    return counts
  }, {})).sort(([, a], [, b]) => b - a), [graph.data])

  if (summary.isLoading || graph.isLoading) return <div className="page"><LoadingState label="Loading interaction graph" /></div>
  if (summary.error || graph.error) return <div className="page"><ErrorState error={summary.error ?? graph.error} /></div>
  const s = summary.data!.summary
  const coverage = communities.data?.coverage
  const name = (id: string) => { const node = nodes.find((item) => item.node_id === id); return node ? nodeLabel(node) : shortNodeLabel(id) }

  return (
    <div className="page">
      <PageHeader title="Interaction map" description="Who replies to, mentions, quotes or forwards whom in the collected data" />
      <Stats label="Graph summary">
        <Stat label="Accounts" value={s.nodes} meta={coverage ? `${formatNumber(coverage.stored_profiles)} with stored profiles` : undefined} />
        <Stat label="Links" value={s.edges} meta={relationships.slice(0, 2).map(([type, count]) => `${count} ${type}`).join(', ')} />
        <Stat label="Communities" value={s.communities} meta="Louvain partition" />
        <Stat label="Density" value={s.density} format={(n) => n.toFixed(4)} />
      </Stats>

      <div className="grid">
        <Panel className="col-8" title="Graph" description="Most recent links. Node size is PageRank, colour is community.">
          <NetworkGraph graph={graph.data!} onSelect={setSelected} selected={selected} focusedCommunity={community} />
          {relationships.length > 0 && <div className="legend" style={{ marginTop: 10 }}>{relationships.map(([type, count]) => <span key={type}>{sentenceCase(type)} <b className="num" style={{ color: 'var(--text)' }}>{count}</b></span>)}</div>}
        </Panel>

        <Panel
          className="col-4"
          flush
          title={selectedNode ? nodeLabel(selectedNode) : 'Top accounts'}
          description={selectedNode ? platformLabel(selectedNode.node_id.split(':')[0]) : 'By PageRank in the loaded graph'}
          actions={selectedNode && <button type="button" className="btn btn--ghost btn--icon" onClick={() => setSelected(null)} aria-label="Back to ranking"><X size={15} /></button>}
        >
          {selectedNode ? (
            <div className="panel__body" style={{ display: 'grid', gap: 14 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <AccountAvatar node={selectedNode} size={44} />
                <div>
                  <div className="row__title">{selectedNode.profile?.username ? `@${selectedNode.profile.username}` : shortNodeLabel(selectedNode.node_id)}</div>
                  <div className="faint" style={{ fontSize: 12 }}>{selectedNode.profile?.status === 'stored_profile' ? 'Profile collected' : 'Only referenced by others'}</div>
                  {profileLink(selectedNode) && <a className="link" style={{ color: 'var(--accent)', fontSize: 12.5 }} href={profileLink(selectedNode)!} target="_blank" rel="noopener noreferrer">View profile <ExternalLink size={11} style={{ display: 'inline' }} /></a>}
                </div>
              </div>
              <dl className="kv num">
                <dt>Community</dt><dd><span className="swatch" style={{ background: communityColor(selectedNode.community), marginRight: 6, display: 'inline-block' }} />{selectedNode.community ?? '–'}</dd>
                <dt>PageRank</dt><dd>{selectedNode.pagerank.toFixed(5)}</dd>
                <dt>Betweenness</dt><dd>{selectedNode.betweenness_centrality.toFixed(5)}</dd>
                <dt>Authority / hub</dt><dd>{selectedNode.authority_score.toFixed(4)} / {selectedNode.hub_score.toFixed(4)}</dd>
              </dl>
              <div>
                <div className="faint" style={{ fontSize: 12, marginBottom: 6 }}>Links</div>
                <div className="rows">
                  {graph.data!.edges.filter((edge) => edge.source === selected || edge.target === selected).slice(0, 8).map((edge) => (
                    <div className="row" style={{ padding: '6px 0' }} key={[edge.event_id, edge.source, edge.target].join(':')}>
                      <div><span className="row__title" style={{ fontSize: 13 }}>{edge.source === selected ? '→ ' : '← '}{name(edge.source === selected ? edge.target : edge.source)}</span><div className="row__meta">{edge.interaction_type} · {formatShortTime(edge.occurred_at)}</div></div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="rows">
              {ranking.map((node, index) => (
                <button type="button" className="row" key={node.node_id} onClick={() => setSelected(node.node_id)} style={{ gridTemplateColumns: '20px 32px minmax(0,1fr) auto' }}>
                  <span className="faint num">{index + 1}</span>
                  <AccountAvatar node={node} size={28} />
                  <span><span className="row__title truncate" style={{ display: 'block' }}>{nodeLabel(node)}</span><span className="row__meta">{platformLabel(node.node_id.split(':')[0])} · community {node.community ?? '–'}</span></span>
                  <span className="row__value">{node.pagerank.toFixed(3)}</span>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel flush title="Communities" description={communities.data ? `${communities.data.communities.length} groups in the recent-link sample. Select one to isolate it on the graph.` : undefined}>
        {communities.isLoading ? <div className="panel__body"><LoadingState /></div> : communities.error ? <div className="panel__body"><ErrorState error={communities.error} /></div> : !communities.data?.communities.length ? <div className="panel__body"><EmptyState title="No communities yet" /></div> : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Community</th><th className="r">Accounts</th><th className="r">Links</th><th>Main link types</th><th>Language</th><th>Country</th><th>Sector</th><th /></tr></thead>
              <tbody>
                {communities.data.communities.slice(0, 10).map((item) => {
                  const top = (key: string) => {
                    const signal = item.audience?.[key]
                    const best = signal && Object.entries(signal.distribution).sort((a, b) => b[1] - a[1])[0]
                    return signal?.status === 'AVAILABLE' && best ? `${best[0]} (${best[1]})` : '–'
                  }
                  const active = community === item.community_id
                  return (
                    <tr key={item.community_id}>
                      <td><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span className="swatch" style={{ background: communityColor(item.community_id) }} /><strong>{item.community_id}</strong></span></td>
                      <td className="r">{item.size}</td>
                      <td className="r">{item.interaction_volume}</td>
                      <td>{item.dominant_interaction_types.join(', ') || '–'}</td>
                      <td>{top('language')}</td><td>{top('geography')}</td><td>{top('profession')}</td>
                      <td className="r"><button type="button" className="btn btn--sm" aria-pressed={active} onClick={() => { setSelected(null); setCommunity(active ? null : item.community_id); document.getElementById('audience-network-map')?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }) }}>{active ? 'Show all' : 'Isolate'}</button></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <div className="grid">
        <Panel className="col-6" flush title="Centrality" description="Whole stored graph">
          {influence.isLoading ? <div className="panel__body"><LoadingState /></div> : influence.error ? <div className="panel__body"><ErrorState error={influence.error} /></div> : !influence.data?.items.length ? <div className="panel__body"><EmptyState title="Not enough links" /></div> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Account</th><th className="r">PageRank</th><th className="r">Betweenness</th><th className="r">Authority</th></tr></thead>
              <tbody>{influence.data.items.map((node) => <tr key={node.node_id} className="is-clickable" onClick={() => setSelected(node.node_id)}><td className="truncate" style={{ maxWidth: 220 }}><strong>{nodeLabel(node)}</strong></td><td className="r">{node.pagerank.toFixed(4)}</td><td className="r">{node.betweenness_centrality.toFixed(4)}</td><td className="r">{node.authority_score.toFixed(4)}</td></tr>)}</tbody>
            </table></div>
          )}
        </Panel>
        <Panel className="col-6" flush title="Snapshots" description="Graph measured in consecutive source-time windows" actions={<Segmented label="Window" value={window} options={WINDOWS} onChange={setWindow} />}>
          {temporal.isLoading ? <div className="panel__body"><LoadingState /></div> : temporal.error ? <div className="panel__body"><ErrorState error={temporal.error} /></div> : !temporal.data?.snapshots.some((snapshot) => snapshot.edges) ? <div className="panel__body"><EmptyState title="No links in these windows" /></div> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Window ending</th><th className="r">Accounts</th><th className="r">Links</th><th className="r">Communities</th><th className="r">Density</th></tr></thead>
              <tbody>{temporal.data.snapshots.map((snapshot) => <tr key={snapshot.window_end}><td className="num">{formatShortTime(snapshot.window_end)}</td><td className="r">{snapshot.nodes}</td><td className="r">{snapshot.edges}</td><td className="r">{snapshot.communities}</td><td className="r">{snapshot.density.toFixed(4)}</td></tr>)}</tbody>
            </table></div>
          )}
          {(temporal.data?.influence_changes.length ?? 0) > 0 && (
            <div className="rows" style={{ borderTop: '1px solid var(--line)' }}>
              {temporal.data!.influence_changes.slice(0, 5).map((delta) => (
                <div className="row" key={`${delta.node_id}-${delta.metric}`}>
                  <div><div className="row__title" style={{ fontSize: 13 }}>{name(delta.node_id)}</div><div className="row__meta">{delta.direction} across {delta.windows_measured} windows</div></div>
                  <div className={`row__value delta ${delta.change >= 0 ? 'delta--up' : 'delta--down'}`}>{delta.first_value.toFixed(3)} → {delta.last_value.toFixed(3)}</div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="grid">
        <Panel className={cascadeId ? 'col-7' : 'col-12'} flush title="Cascades" description="Reply and forward chains reconstructed from stored parent links">
          {cascades.isLoading ? <div className="panel__body"><LoadingState /></div> : cascades.error ? <div className="panel__body"><ErrorState error={cascades.error} /></div> : !cascades.data?.count ? <div className="panel__body"><EmptyState title="No cascades yet" detail="Chains appear when collected posts reference collected parents." /></div> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Root</th><th className="r">Events</th><th className="r">Depth</th><th className="r">Width</th><th className="r">Duration</th><th>Started</th></tr></thead>
                <tbody>{cascades.data.cascades.slice(0, 12).map((item) => (
                  <tr key={item.cascade_id} className="is-clickable" tabIndex={0} aria-selected={cascadeId === item.cascade_id} onClick={() => setCascadeId(item.cascade_id)} onKeyDown={(event) => { if (event.key === 'Enter') setCascadeId(item.cascade_id) }} style={cascadeId === item.cascade_id ? { background: 'var(--surface-2)' } : undefined}>
                    <td><strong>{platformLabel(item.platform)}</strong> <span className="faint mono">{item.root_platform_post_id.slice(-14)}</span></td>
                    <td className="r">{item.event_count}</td><td className="r">{item.depth}</td><td className="r">{item.width}</td>
                    <td className="r">{item.duration_seconds != null ? formatDuration(item.duration_seconds) : '–'}</td>
                    <td className="num">{formatShortTime(item.started_at)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </Panel>
        {cascadeId && (
          <Panel className="col-5" title="Propagation" description={cascade.data ? `${cascade.data.event_count} events, ${cascade.data.participant_count} accounts` : undefined} actions={<button type="button" className="btn btn--ghost btn--icon" onClick={() => setCascadeId(null)} aria-label="Close cascade"><X size={15} /></button>}>
            {cascade.isLoading ? <LoadingState /> : cascade.error ? <ErrorState error={cascade.error} /> : cascade.data && (
              <ol className="path">
                {cascade.data.propagation_path.map((step) => (
                  <li key={step.event_id}>
                    <b>{step.depth}</b>
                    <div><span className="row__title" style={{ fontSize: 13 }}>{name(step.node_id)}</span><div className="row__meta">{step.interaction_type}{step.sentiment ? ` · ${step.sentiment}` : ''}{step.is_ironic ? ' · ironic' : ''}</div></div>
                    <span className="faint num" style={{ fontSize: 12 }}>{formatShortTime(step.occurred_at)}</span>
                  </li>
                ))}
              </ol>
            )}
          </Panel>
        )}
      </div>

      <p className="faint" style={{ fontSize: 12.5, maxWidth: 900 }}>{s.interpretation}</p>
    </div>
  )
}
