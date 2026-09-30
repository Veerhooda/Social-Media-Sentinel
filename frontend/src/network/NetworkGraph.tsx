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
}

export function NetworkGraph({ graph, onSelect, selected = null }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const sigma = useRef<Sigma | null>(null)
  const selectedRef = useRef<string | null>(selected)
  const onSelectRef = useRef(onSelect)
  const [view, setView] = useState<'core' | 'all'>('core')
  const visible = useMemo(() => view === 'core' ? connectedCore(graph) : graph, [graph, view])
  const visualGraph = useMemo(() => buildVisualGraph(visible), [visible])

  useEffect(() => { selectedRef.current = selected; sigma.current?.refresh() }, [selected])
  useEffect(() => { onSelectRef.current = onSelect }, [onSelect])

  useEffect(() => {
    if (!container.current || visualGraph.order === 0) return
    let disposed = false
    let renderer: Sigma | null = null
    void Promise.all([import('sigma'), import('sigma/rendering')]).then(([sigmaModule, rendering]) => {
      if (disposed || !container.current) return
      renderer = new sigmaModule.default(visualGraph, container.current, {
        edgeProgramClasses: { arrow: rendering.EdgeArrowProgram },
        defaultEdgeType: 'arrow',
        labelFont: 'Inter, system-ui, sans-serif',
        labelSize: 13,
        labelWeight: '600',
        labelColor: { color: '#f5f5f2' },
        labelDensity: 0.6,
        labelRenderedSizeThreshold: 11,
        stagePadding: 38,
        minCameraRatio: 0.12,
        maxCameraRatio: 3,
        nodeReducer: (node, data) => {
          const current = selectedRef.current
          if (!current) return data
          const adjacent = node === current || visualGraph.areNeighbors(node, current)
          return { ...data, color: adjacent ? data.color : '#47494b', label: adjacent ? data.label : '' }
        },
        edgeReducer: (edge, data) => {
          const current = selectedRef.current
          if (!current) return data
          const connected = visualGraph.extremities(edge).includes(current)
          return { ...data, color: connected ? '#f6de62' : '#36383a', size: connected ? 2 : 0.6 }
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

  if (!graph.nodes.length) return <EmptyState title="No interaction network" detail="Edges appear after replies, mentions, quotes, or reposts are collected." />

  const zoom = (factor: number) => {
    const camera = sigma.current?.getCamera()
    if (camera) void camera.animate({ ratio: Math.max(0.12, Math.min(3, camera.ratio * factor)) }, { duration: 220 })
  }

  return (
    <div className="network-canvas">
      <div className="network-canvas__caption">
        <strong>Interaction map</strong>
        <span>{visible.node_count} of {graph.node_count} accounts in loaded graph · {visible.edge_count} visible relationships</span>
      </div>
      <div className="network-view-switch" role="group" aria-label="Network detail">
        <button type="button" className={view === 'core' ? 'is-active' : ''} aria-pressed={view === 'core'} onClick={() => setView('core')}>Connected core</button>
        <button type="button" className={view === 'all' ? 'is-active' : ''} aria-pressed={view === 'all'} onClick={() => setView('all')}>All loaded</button>
      </div>
      <div className="network-controls" role="group" aria-label="Network view controls">
        <button type="button" onClick={() => zoom(0.72)} aria-label="Zoom in"><Plus size={18} /></button>
        <button type="button" onClick={() => zoom(1.38)} aria-label="Zoom out"><Minus size={18} /></button>
        <button type="button" onClick={() => sigma.current?.getCamera().animatedReset({ duration: 220 })} aria-label="Reset network view"><Maximize2 size={17} /></button>
      </div>
      <div ref={container} className="network-canvas__renderer" role="img" aria-label="Directed interaction network. Use the ranked list to select accounts with a keyboard." />
      {!visible.edges.length && <p className="network-canvas__notice">No verified relationships in this selection.</p>}
      <div className="network-canvas__footer">
        <span>Recent-edge sample · drag to pan · scroll to zoom · select an account</span>
        {selected && <button type="button" onClick={() => onSelect?.(null)}>Clear {shortNodeLabel(selected)} selection</button>}
      </div>
    </div>
  )
}
