import { vi } from 'vitest'

/** Stubs fetch with a route table: first matching substring wins. Records every call. */
export function stubApi(routes: [string, unknown | ((init?: RequestInit) => unknown)][]) {
  const calls: { url: string; init?: RequestInit }[] = []
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    calls.push({ url, init })
    const match = routes.find(([pattern]) => url.includes(pattern))
    if (!match) return Promise.resolve(new Response(JSON.stringify({ detail: `no stub for ${url}` }), { status: 404 }))
    const body = typeof match[1] === 'function' ? (match[1] as (init?: RequestInit) => unknown)(init) : match[1]
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
  })
  vi.stubGlobal('fetch', fetchMock)
  return calls
}

export const health = (platforms: unknown[] = []) => ({
  status: 'PASS',
  database: { status: 'PASS', detail: 'PostgreSQL reachable' },
  x_api: { status: 'SKIPPED', detail: 'X_BEARER_TOKEN is not configured' },
  telegram_api: { status: 'PASS', detail: 'configured' },
  youtube_api: { status: 'PASS', detail: 'configured' },
  scheduler: { status: 'PASS', detail: 'running' },
  analytics: { status: 'PASS', detail: 'running' },
  event_count: 450,
  real_event_count: 446,
  replay_event_count: 4,
  updated_at: '2026-10-03T00:00:00Z',
  platforms,
})

export const jobs = (list: unknown[] = [], running = true) => ({ enabled: true, running, started_at: '2026-10-03T00:00:00Z', stopped_at: null, jobs: list })

export const point = (end: string, positive: number, negative: number, count = 10) => ({
  window_start: end, window_end: end, event_count: count, positive_ratio: positive, neutral_ratio: 1 - positive - negative,
  negative_ratio: negative, emotion_distribution: { neutral: 0.6, joy: 0.2, anger: 0.1 }, anxiety_average: 0.05,
  excitement_average: 0.1, irony_rate: 0.12, stance_distribution: {},
})
