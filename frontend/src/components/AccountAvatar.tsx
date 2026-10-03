import { useState } from 'react'
import type { NodeMetrics } from '../types/network'
import { communityColor, nodeLabel } from '../utils/network'

export function AccountAvatar({ node, size = 32 }: { node: NodeMetrics; size?: number }) {
  const [failed, setFailed] = useState(false)
  const url = node.profile?.status === 'stored_profile' ? node.profile.avatar_url : null
  const initial = node.profile?.status === 'stored_profile' ? nodeLabel(node).replace(/^@/, '').slice(0, 1).toUpperCase() : '?'
  return (
    <span className="avatar" style={{ width: size, height: size, borderColor: communityColor(node.community) }} aria-hidden="true">
      {url && !failed ? <img src={url} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} /> : initial}
    </span>
  )
}
