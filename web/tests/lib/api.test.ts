import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ApiError, api, http } from '@/lib/api'

const originalFetch = globalThis.fetch

beforeEach(() => { globalThis.fetch = vi.fn() as unknown as typeof fetch })
afterEach(() => { globalThis.fetch = originalFetch })

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } })
}
function err(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

describe('http', () => {
  it('unwraps the data envelope', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(ok({ data: { hello: 'world' }, meta: {} }))
    const out = await http<{ hello: string }>('/api/test')
    expect(out).toEqual({ hello: 'world' })
  })

  it('throws ApiError with code + message on 4xx', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      err(404, { error: { code: 'not_found', message: 'no such symbol', details: { symbol: 'XXX' } } })
    )
    await expect(http('/api/test')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'not_found',
      message: 'no such symbol',
      status: 404,
      details: { symbol: 'XXX' },
    })
  })

  it('throws ApiError even when body is not JSON', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('boom', { status: 500 })
    )
    await expect(http('/api/test')).rejects.toBeInstanceOf(ApiError)
  })
})

describe('api.listSymbols', () => {
  it('forwards q and market as query params', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(ok({ data: [], meta: { count: 0 } }))
    await api.listSymbols({ q: '000', market: 'SZ' })
    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]![0] as string
    expect(url).toContain('q=000')
    expect(url).toContain('market=SZ')
  })

  it('passes no query string when no opts', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(ok({ data: [], meta: { count: 0 } }))
    await api.listSymbols()
    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]![0] as string
    expect(url).toBe('/api/symbols')
  })
})

describe('api.submitSelectionJob', () => {
  it('POSTs JSON body', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(ok({ data: { job_id: 'abc' }, meta: {} }))
    const body = { as_of_date: null, config: { top_n: 5 }, symbol_universe: null }
    const out = await api.submitSelectionJob(body)
    expect(out).toEqual({ job_id: 'abc' })
    const init = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0]![1] as RequestInit
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify(body))
  })
})
