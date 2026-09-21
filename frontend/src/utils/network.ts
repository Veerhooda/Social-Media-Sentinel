import type { NetworkGraphResponse, NodeMetrics } from '../types/network'

export interface PositionedNode extends NodeMetrics {
  x: number
  y: number
  radius: number
}

export function positionNetwork(graph: NetworkGraphResponse, width = 760, height = 460): PositionedNode[] {
  const communities = new Map<number, NodeMetrics[]>()
  graph.nodes.forEach((node) => {
    const community = node.community ?? -1
    communities.set(community, [...(communities.get(community) ?? []), node])
  })
  const groups = [...communities.entries()].sort(([left], [right]) => left - right)
  const centerX = width / 2
  const centerY = height / 2
  return groups.flatMap(([, nodes], groupIndex) => {
    const groupAngle = (groupIndex / Math.max(groups.length, 1)) * Math.PI * 2 - Math.PI / 2
    const groupDistance = groups.length === 1 ? 0 : Math.min(width, height) * 0.27
    const groupX = centerX + Math.cos(groupAngle) * groupDistance
    const groupY = centerY + Math.sin(groupAngle) * groupDistance
    return nodes.map((node, nodeIndex) => {
      const angle = (nodeIndex / Math.max(nodes.length, 1)) * Math.PI * 2
      const spread = 28 + Math.sqrt(nodes.length) * 12
      return {
        ...node,
        x: groupX + Math.cos(angle) * spread,
        y: groupY + Math.sin(angle) * spread,
        radius: 5 + Math.sqrt(Math.max(node.pagerank, 0) * 450),
      }
    })
  })
}

