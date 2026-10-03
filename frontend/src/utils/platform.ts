const LABELS: Record<string, string> = { x: 'X', telegram: 'Telegram', youtube: 'YouTube' }

export const platformLabel = (platform: string) => LABELS[platform] ?? platform.charAt(0).toUpperCase() + platform.slice(1)
