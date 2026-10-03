import Graph from 'graphology'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import type { NetworkGraphResponse, NodeMetrics } from '../types/network'

export const COMMUNITY_COLORS = ['#4361ee', '#d66a39', '#148b78', '#a05ca7', '#c89b2b', '#3983a9', '#a45d57']

export function communityColor(community: number | null): string {
  return community == null ? '#64748b' : COMMUNITY_COLORS[Math.abs(community) % COMMUNITY_COLORS.length]
}

export function shortNodeLabel(id: string): string {
  const suffix = id.split(':').slice(1).join(':') || id
  return suffix.length > 24 ? `${suffix.slice(0, 21)}…` : suffix
}

export function nodeLabel(node: NodeMetrics): string {
  if (node.profile?.status === 'stored_profile') {
    return node.profile.display_name || (node.profile.username ? `@${node.profile.username}` : shortNodeLabel(node.node_id))
  }
  return shortNodeLabel(node.node_id)
}

export function profileLink(node: NodeMetrics): string | null {
  const username = node.profile?.username
  if (node.profile?.status !== 'stored_profile' || !username) return null
  if (node.node_id.startsWith('x:') && /^[A-Za-z0-9_]{1,15}$/.test(username)) return `https://x.com/${username}`
  if (node.node_id.startsWith('telegram:') && /^[A-Za-z0-9_]{5,32}$/.test(username)) return `https://t.me/${username}`
  return null
}

export function connectedCore(data: NetworkGraphResponse, limit = 90): NetworkGraphResponse {
  const degree = new Map<string, number>()
  data.edges.forEach((edge) => {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1)
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1)
  })
  const nodes = [...data.nodes]
    .filter((node) => degree.has(node.node_id))
    .sort((a, b) => (degree.get(b.node_id)! - degree.get(a.node_id)!) || b.pagerank - a.pagerank || a.node_id.localeCompare(b.node_id))
    .slice(0, limit)
  const included = new Set(nodes.map((node) => node.node_id))
  const edges = data.edges.filter((edge) => included.has(edge.source) && included.has(edge.target))
  return { nodes, edges, node_count: nodes.length, edge_count: edges.length }
}

export function buildVisualGraph(data: NetworkGraphResponse): Graph {
  const graph = new Graph({ type: 'directed', multi: false, allowSelfLoops: false })
  const ordered = [...data.nodes].sort((a, b) => a.node_id.localeCompare(b.node_id))
  const maxRank = Math.max(...ordered.map((node) => node.pagerank), 0)

  ordered.forEach((node: NodeMetrics, index) => {
    const angle = index * 2.399963229728653
    const radius = 1.5 * Math.sqrt(index + 1)
    graph.addNode(node.node_id, {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      size: 5 + (maxRank ? Math.sqrt(node.pagerank / maxRank) * 11 : 0),
      color: communityColor(node.community),
      label: node.profile?.status === 'stored_profile' ? nodeLabel(node) : '',
      rank: node.pagerank,
      community: node.community,
      ...(node.profile?.status === 'stored_profile' && node.profile.avatar_url?.startsWith('https://') ? {
        image: node.profile.avatar_url,
        type: 'image',
      } : {}),
    })
  })

  // The API returns event-level edges. Aggregate parallel interactions for
  // display while retaining count and total configured weight in the graph.
  data.edges.forEach((edge) => {
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target) || edge.source === edge.target) return
    if (graph.hasEdge(edge.source, edge.target)) {
      const key = graph.edge(edge.source, edge.target)!
      graph.updateEdgeAttribute(key, 'weight', (weight: number) => weight + edge.weight)
      graph.updateEdgeAttribute(key, 'count', (count: number) => count + 1)
    } else {
      graph.addDirectedEdge(edge.source, edge.target, {
        weight: edge.weight,
        count: 1,
        color: '#55585b',
        size: 1.3,
        type: 'arrow',
      })
    }
  })

  if (graph.order > 1 && graph.size > 0) {
    forceAtlas2.assign(graph, {
      iterations: Math.min(140, Math.max(45, graph.order * 2)),
      settings: { ...forceAtlas2.inferSettings(graph), gravity: 0.7, scalingRatio: 12 },
    })
  }
  return graph
}
