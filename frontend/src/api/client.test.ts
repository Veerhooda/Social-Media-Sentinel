import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiRequest, queryString } from './client'

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('returns typed JSON from the centralized API base', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'PASS' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiRequest<{ status: string }>('/health')).resolves.toEqual({ status: 'PASS' })
    expect(fetchMock).toHaveBeenCalledWith('/api/health', expect.objectContaining({ headers: expect.objectContaining({ Accept: 'application/json' }) }))
  })

  it('surfaces backend error details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Database unavailable' }), { status: 503 })))
    const error = await apiRequest('/health').catch((caught: unknown) => caught)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 503, message: 'Database unavailable' })
  })

  it('encodes pagination and filters without undefined values', () => {
    expect(queryString({ limit: 50, offset: 0, platform: undefined, newest_first: true })).toBe('?limit=50&offset=0&newest_first=true')
  })
})
