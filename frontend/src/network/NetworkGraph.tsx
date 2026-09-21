import { Minus, Plus } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { NetworkGraphResponse } from '../types/network'
import { positionNetwork } from '../utils/network'
import { EmptyState } from '../components/States'

const communityColors = ['#ff7a00', '#2563eb', '#10b981', '#e11d48', '#8b5cf6', '#0ea5e9', '#f59e0b']

export function NetworkGraph({ graph, onSelect }: { graph: NetworkGraphResponse; onSelect?: (nodeId: string) => void }) {
  const [zoom, setZoom] = useState(1)
  const nodes = useMemo(() => positionNetwork(graph), [graph])
  const positions = useMemo(() => new Map(nodes.map((node) => [node.node_id, node])), [nodes])
  if (!nodes.length) return <EmptyState title="No interaction network" detail="Edges appear after replies, mentions, quotes, or reposts are collected." />
  return (
    <div className="network-canvas">
      <div className="network-controls">
        <button type="button" onClick={() => setZoom((value) => Math.min(1.7, value + 0.15))} aria-label="Zoom in"><Plus size={15} /></button>
        <button type="button" onClick={() => setZoom((value) => Math.max(0.65, value - 0.15))} aria-label="Zoom out"><Minus size={15} /></button>
      </div>
      <svg viewBox="0 0 760 460" role="img" aria-label="Interaction-derived influence network">
        <g transform={`translate(${380 - 380 * zoom} ${230 - 230 * zoom}) scale(${zoom})`}>
          {graph.edges.map((edge, index) => {
            const source = positions.get(edge.source)
            const target = positions.get(edge.target)
            if (!source || !target) return null
            return <line key={`${edge.event_id}-${index}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#d9dee7" strokeWidth={Math.max(0.7, edge.weight * 1.2)} opacity="0.62" />
          })}
          {nodes.map((node) => (
            <g key={node.node_id} transform={`translate(${node.x} ${node.y})`} onClick={() => onSelect?.(node.node_id)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') onSelect?.(node.node_id) }} className="network-node" tabIndex={0} role="button" aria-label={`Network node ${node.node_id}`}>
              <circle r={node.radius + 3} fill="white" stroke={communityColors[(node.community ?? 0) % communityColors.length]} strokeWidth="2.5" />
              <circle r={node.radius} fill={communityColors[(node.community ?? 0) % communityColors.length]} opacity="0.84" />
              <title>{`${node.node_id} · PageRank ${node.pagerank.toFixed(4)}`}</title>
            </g>
          ))}
        </g>
      </svg>
    </div>
  )
}
