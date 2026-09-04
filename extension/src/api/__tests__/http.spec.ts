import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'

import { request } from '../http'

const schema = z.object({ ok: z.boolean() })

/** Narrow a Result to its error, failing the test if it succeeded. */
function expectError(result: Awaited<ReturnType<typeof request>>) {
  if (result.ok) throw new Error('expected a failure, got a success')
  return result.error
}
const URL = 'https://vault.example.com/api/thing'

function respond(status: number, body: unknown = {}, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('request', () => {
  it('returns the parsed body on success', async () => {
    fetchMock.mockResolvedValue(respond(200, { ok: true }))

    const result = await request({ url: URL }, schema)

    expect(result).toEqual({ ok: true, data: { ok: true } })
  })

  it('ignores unknown keys so a newer vault does not break an older extension', async () => {
    // Version skew is normal when the vault is self-hosted.
    fetchMock.mockResolvedValue(respond(200, { ok: true, somethingNew: 42 }))

    const result = await request({ url: URL }, schema)

    expect(result.ok).toBe(true)
  })

  it('attaches the bearer token when given one', async () => {
    fetchMock.mockResolvedValue(respond(200, { ok: true }))

    await request({ url: URL, bearerToken: 'tok' }, schema)

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer tok')
  })

  it('never sends cookies', async () => {
    // They would not be attached anyway (SameSite=strict); omitting them makes
    // the intent explicit: bearer or nothing.
    fetchMock.mockResolvedValue(respond(200, { ok: true }))

    await request({ url: URL }, schema)

    expect(fetchMock.mock.calls[0][1].credentials).toBe('omit')
  })

  it('reports an unreachable vault when fetch throws', async () => {
    // Also what a fetch made without the host permission looks like, which is
    // why callers check permissions.contains first.
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const result = await request({ url: URL }, schema)

    expect(result).toEqual({ ok: false, error: { kind: 'NETWORK_UNREACHABLE' } })
  })

  it.each([
    [401, { kind: 'AUTH_LOST', reason: 'revoked' }],
    [403, { kind: 'FORBIDDEN' }],
    [404, { kind: 'NOT_FOUND' }],
    [500, { kind: 'SERVER_ERROR', status: 500 }],
  ])('maps %i to a domain error', async (status, expected) => {
    fetchMock.mockResolvedValue(respond(status))

    const result = await request({ url: URL }, schema)

    expect(result).toEqual({ ok: false, error: expected })
  })

  it('tells a locked vault apart from a starting server', async () => {
    // Same status, opposite advice: one needs an admin, the other needs a wait.
    fetchMock.mockResolvedValue(respond(503, { code: 'vault_locked' }))
    await expect(request({ url: URL }, schema)).resolves.toEqual({
      ok: false,
      error: { kind: 'VAULT_LOCKED' },
    })

    fetchMock.mockResolvedValue(respond(503, { code: 'starting' }))
    await expect(request({ url: URL }, schema)).resolves.toEqual({
      ok: false,
      error: { kind: 'SERVER_STARTING' },
    })
  })

  it('assumes a locked vault when a 503 carries no code', async () => {
    fetchMock.mockResolvedValue(respond(503, { detail: 'something' }))

    const result = await request({ url: URL }, schema)

    expect(result).toEqual({ ok: false, error: { kind: 'VAULT_LOCKED' } })
  })

  it('reads Retry-After in seconds', async () => {
    fetchMock.mockResolvedValue(respond(429, {}, { 'Retry-After': '42' }))

    const result = await request({ url: URL }, schema)

    expect(result).toEqual({ ok: false, error: { kind: 'RATE_LIMITED', retryAfterSeconds: 42 } })
  })

  it('reads Retry-After as an http date', async () => {
    const future = new Date(Date.now() + 30_000).toUTCString()
    fetchMock.mockResolvedValue(respond(429, {}, { 'Retry-After': future }))

    const result = await request({ url: URL }, schema)

    const error = expectError(result)
    expect(error.kind).toBe('RATE_LIMITED')
    expect(error).toMatchObject({ kind: 'RATE_LIMITED' })
    const seconds = (error as { retryAfterSeconds: number }).retryAfterSeconds
    expect(seconds).toBeGreaterThan(25)
    expect(seconds).toBeLessThanOrEqual(30)
  })

  it('falls back to a default when Retry-After is missing', async () => {
    fetchMock.mockResolvedValue(respond(429))

    const result = await request({ url: URL }, schema)

    expect(result).toEqual({ ok: false, error: { kind: 'RATE_LIMITED', retryAfterSeconds: 60 } })
  })

  it('reports a protocol mismatch rather than throwing on an unexpected shape', async () => {
    // What a vault months behind the extension looks like. Throwing a TypeError
    // deep in a component would tell the user nothing.
    fetchMock.mockResolvedValue(respond(200, { unexpected: 'shape' }))

    const result = await request({ url: URL }, schema)

    expect(expectError(result).kind).toBe('PROTOCOL_MISMATCH')
  })

  it('reports a non-vault when the body is not json', async () => {
    fetchMock.mockResolvedValue(new Response('<html>hello</html>', { status: 200 }))

    const result = await request({ url: URL }, schema)

    expect(result).toEqual({ ok: false, error: { kind: 'NOT_A_VAULT' } })
  })
})
