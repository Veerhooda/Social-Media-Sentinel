export function PlatformBadge({ platform }: { platform: string }) {
  return <span className={`platform-badge platform-badge--${platform}`}>{platform === 'x' ? 'X' : platform}</span>
}

