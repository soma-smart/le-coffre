import { describe, expect, it } from 'vitest'

import { entrySchema, exchangePairingSchema, startPairingSchema } from '../schemas'

const entry = {
  id: 'e1',
  name: 'Production database',
  folder: 'infra',
  group_id: 'g1',
  login: 'dba',
  url: null,
  can_read: true,
  can_write: true,
  accessible_group_ids: [],
}

function parsesWithExpiry(stamp: string): boolean[] {
  return [
    startPairingSchema.safeParse({ user_code: 'K', expires_at: stamp, poll_interval_seconds: 5 })
      .success,
    exchangePairingSchema.safeParse({ status: 'pending', expires_at: stamp }).success,
    entrySchema.safeParse({ ...entry, access_expires_at: stamp }).success,
  ]
}

describe('expiry timestamps', () => {
  it.each(['2026-08-27T12:00:00Z', '2026-08-27T12:00:00.123456+00:00', '2026-08-27T12:00:00'])(
    'accepts %s, the forms pydantic emits',
    (stamp) => {
      expect(parsesWithExpiry(stamp)).toEqual([true, true, true])
    },
  )

  it.each(['never', '', '27/08/2026', '1756296000'])('refuses %s', (garbage) => {
    // new Date(garbage).getTime() is NaN, and every comparison with NaN is
    // false, so an unparsable expiry used to read as "never expires".
    expect(parsesWithExpiry(garbage)).toEqual([false, false, false])
  })

  it('still allows a share with no expiry', () => {
    expect(entrySchema.safeParse({ ...entry, access_expires_at: null }).success).toBe(true)
    expect(entrySchema.safeParse(entry).success).toBe(true)
  })
})
