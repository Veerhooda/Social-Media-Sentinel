import { useState } from 'react'
import type { NodeMetrics } from '../types/network'
import { communityColor, nodeLabel } from '../utils/network'

export function AccountAvatar({ node, size = 38 }: { node: NodeMetrics; size?: number }) {
  const [failed, setFailed] = useState(false)
  const url = node.profile?.status === 'stored_profile' ? node.profile.avatar_url : null
  const fallback = node.profile?.status === 'stored_profile'
    ? nodeLabel(node).replace(/^@/, '').slice(0, 1).toUpperCase()
    : '?'
  return (
    <span className="account-avatar" style={{ width: size, height: size, borderColor: communityColor(node.community) }} aria-hidden="true">
      {url && !failed ? <img src={url} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} /> : fallback}
    </span>
  )
}
