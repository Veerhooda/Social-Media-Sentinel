import { AtSign, Play, Send, Globe } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const PLATFORMS: Record<string, { label: string; icon: LucideIcon }> = {
  x: { label: 'X', icon: AtSign },
  telegram: { label: 'Telegram', icon: Send },
  youtube: { label: 'YouTube', icon: Play },
}

import { platformLabel } from '../utils/platform'

export function PlatformIcon({ platform, size = 14 }: { platform: string; size?: number }) {
  const Icon = PLATFORMS[platform]?.icon ?? Globe
  return <Icon size={size} aria-hidden="true" />
}

export function Platform({ platform }: { platform: string }) {
  return <span className="platform"><PlatformIcon platform={platform} />{platformLabel(platform)}</span>
}
