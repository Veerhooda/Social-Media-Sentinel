import { Maximize2, Minus, Plus } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type Sigma from 'sigma'
import type { NetworkGraphResponse } from '../types/network'
import { buildVisualGraph, connectedCore, shortNodeLabel } from '../utils/network'
import { EmptyState } from '../components/States'

interface Props {
  graph: NetworkGraphResponse
  onSelect?: (nodeId: string | null) => void
  selected?: string | null
  focusedCommunity?: number | null
}

export function NetworkGraph({ graph, onSelect, selected = null, focusedCommunity = null }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const sigma = useRef<Sigma | null>(null)
  const selectedRef = useRef<string | null>(selected)
  const communityRef = useRef<number | null>(focusedCommunity)
  const onSelectRef = useRef(onSelect)
  const [view, setView] = useState<'core' | 'all'>('core')
  const visible = useMemo(() => {
    if (focusedCommunity !== null) {
      const nodes = graph.nodes.filter((node) => node.community === focusedCommunity)
      const ids = new Set(nodes.map((node) => node.node_id))
      const edges = graph.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target))
      return { nodes, edges, node_count: nodes.length, edge_count: edges.length }
    }
    return view === 'core' ? connectedCore(graph) : graph
  }, [graph, view, focusedCommunity])
  const visualGraph = useMemo(() => buildVisualGraph(visible), [visible])

  useEffect(() => { selectedRef.current = selected; sigma.current?.refresh() }, [selected])
  useEffect(() => { communityRef.current = focusedCommunity; if (focusedCommunity === null) setView('core'); sigma.current?.refresh() }, [focusedCommunity])
  useEffect(() => { if (selected && !visible.nodes.some((node) => node.node_id === selected)) setView('all') }, [selected, visible.nodes])
  useEffect(() => { onSelectRef.current = onSelect }, [onSelect])

  useEffect(() => {
    if (!container.current || visualGraph.order === 0) return
    let disposed = false
    let renderer: Sigma | null = null
    void Promise.all([import('sigma'), import('sigma/rendering'), import('@sigma/node-image')]).then(([sigmaModule, rendering, imageRendering]) => {
      if (disposed || !container.current) return
      renderer = new sigmaModule.default(visualGraph, container.current, {
        nodeProgramClasses: { image: imageRendering.NodeImageProgram },
        edgeProgramClasses: { arrow: rendering.EdgeArrowProgram },
        defaultEdgeType: 'arrow',
        labelFont: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        labelSize: 12,
        labelWeight: '500',
        labelColor: { color: '#d7d9dc' },
        labelDensity: 0.6,
        labelRenderedSizeThreshold: 11,
        stagePadding: 38,
        minCameraRatio: 0.12,
        maxCameraRatio: 3,
        nodeReducer: (node, data) => {
          const current = selectedRef.current
          if (!current && communityRef.current !== null) {
            return visualGraph.getNodeAttribute(node, 'community') === communityRef.current
              ? data : { ...data, hidden: true }
          }
          if (!current) return data
          const adjacent = node === current || visualGraph.areNeighbors(node, current)
          return adjacent ? data : { ...data, hidden: true }
        },
        edgeReducer: (edge, data) => {
          const current = selectedRef.current
          if (!current && communityRef.current !== null) {
            return visualGraph.extremities(edge).every((node) => visualGraph.getNodeAttribute(node, 'community') === communityRef.current)
              ? data : { ...data, hidden: true }
          }
          if (!current) return data
          const connected = visualGraph.extremities(edge).includes(current)
          return connected ? { ...data, color: '#e9c46a', size: 2 } : { ...data, hidden: true }
        },
      })
      sigma.current = renderer
      renderer.on('clickNode', ({ node }) => onSelectRef.current?.(node))
      renderer.on('clickStage', () => onSelectRef.current?.(null))
    }).catch(() => {
      // The adjacent ranked list remains a keyboard-accessible fallback when
      // WebGL is unavailable (including server-side and test environments).
      sigma.current = null
    })
    return () => { disposed = true; renderer?.kill(); sigma.current = null }
  }, [visualGraph])

  if (!graph.nodes.length) return <EmptyState title="No interactions yet" detail="Links appear once replies, mentions, quotes or forwards are collected." />

  const zoom = (factor: number) => {
    const camera = sigma.current?.getCamera()
    if (camera) void camera.animate({ ratio: Math.max(0.12, Math.min(3, camera.ratio * factor)) }, { duration: 220 })
  }

  return (
    <div className="graph" id="audience-network-map">
      <div className="graph__top">
        <span className="faint num">{visible.node_count} of {graph.node_count} accounts · {visible.edge_count} links</span>
        {focusedCommunity === null && (
          <div className="segmented" role="group" aria-label="Network detail">
            <button type="button" aria-pressed={view === 'core'} onClick={() => setView('core')}>Connected core</button>
            <button type="button" aria-pressed={view === 'all'} onClick={() => setView('all')}>All loaded</button>
          </div>
        )}
      </div>
      <div className="graph__controls" role="group" aria-label="Zoom">
        <button type="button" className="btn btn--icon btn--sm" onClick={() => zoom(0.72)} aria-label="Zoom in"><Plus size={14} /></button>
        <button type="button" className="btn btn--icon btn--sm" onClick={() => zoom(1.38)} aria-label="Zoom out"><Minus size={14} /></button>
        <button type="button" className="btn btn--icon btn--sm" onClick={() => sigma.current?.getCamera().animatedReset({ duration: 220 })} aria-label="Reset view"><Maximize2 size={13} /></button>
      </div>
      <div ref={container} className="graph__canvas" role="img" aria-label="Directed interaction network. Use the ranked list to select accounts with a keyboard." />
      {!visible.edges.length && <p className="graph__notice">No links in this selection.</p>}
      <div className="graph__bottom faint">
        <span>Drag to pan, scroll to zoom, click an account</span>
        {focusedCommunity !== null && <span>Showing community {focusedCommunity}</span>}
        {selected && <button type="button" className="btn btn--ghost btn--sm" onClick={() => onSelect?.(null)}>Clear {shortNodeLabel(selected)}</button>}
      </div>
    </div>
  )
}
