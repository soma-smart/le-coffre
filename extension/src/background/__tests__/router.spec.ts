import { describe, expect, it } from 'vitest'

import { requestSchema } from '@/shared/messageSchemas'

import { HANDLED_REQUEST_TYPES, route } from '../router'
import { createTestDeps, givenPaired } from './testDeps'

describe('route', () => {
  it('should dispatch a well-formed request', async () => {
    const { deps } = createTestDeps()

    const result = await route(deps, { type: 'CONNECTION_GET_STATE' })

    expect(result).toEqual({ ok: true, data: { status: 'unconfigured' } })
  })

  it('should ignore keys the protocol does not know, so a newer popup still works', async () => {
    const { deps } = createTestDeps()

    const result = await route(deps, { type: 'CONNECTION_GET_STATE', extra: 1 })

    expect(result.ok).toBe(true)
  })

  it.each([
    ['nothing', null],
    ['a string', 'CONNECTION_GET_STATE'],
    ['an empty object', {}],
    ['an unknown type', { type: 'NOPE' }],
    ['a missing field', { type: 'ENTRIES_LIST' }],
    ['a field of the wrong type', { type: 'SETTINGS_SET_GROUP', groupId: 42 }],
    ['a value outside the enum', { type: 'CLIPBOARD_COPY', entryId: 'e1', field: 'secret' }],
  ])('should refuse %s with a typed error instead of reaching a handler', async (_, message) => {
    // Anything on the runtime channel lands here. A cast would let
    // `{ type: 'ENTRIES_LIST' }` reach listEntries with groupId undefined,
    // which fails far from the cause, after a network call.
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)

    const result = await route(deps, message)

    expect(result.ok).toBe(false)
    expect(result.ok ? null : result.error.kind).toBe('PROTOCOL_MISMATCH')
    expect(client.revealCalls).toEqual([])
    await expect(browser.local.get('selectedGroupId')).resolves.toBeUndefined()
  })

  it('should name the type in the error when there is one to name', async () => {
    const { deps } = createTestDeps()

    const result = await route(deps, { type: 'ENTRIES_LIST' })

    expect(result.ok ? null : result.error).toEqual({
      kind: 'PROTOCOL_MISMATCH',
      detail: 'malformed request "ENTRIES_LIST"',
    })
  })

  it('should have a schema for every handled request type, and nothing more', () => {
    // messageSchemas.ts pins this at compile time too; this is the runtime
    // twin, so a mismatch fails a test rather than only a type-check.
    const described = requestSchema.options.map((option) => option.shape.type.value).sort()

    expect(described).toEqual([...HANDLED_REQUEST_TYPES].sort())
  })
})
