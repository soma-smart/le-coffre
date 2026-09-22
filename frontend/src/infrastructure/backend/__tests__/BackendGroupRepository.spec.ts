import { describe, expect, it } from 'vitest'
import { toGroupEventData } from '@/infrastructure/backend/BackendGroupRepository'

describe('toGroupEventData', () => {
  it('returns an empty object for null / undefined / non-object input', () => {
    expect(toGroupEventData(null)).toEqual({})
    expect(toGroupEventData(undefined)).toEqual({})
    expect(toGroupEventData('not an object')).toEqual({})
    expect(toGroupEventData(42)).toEqual({})
  })

  it('camelCases the keys emitted by membership events', () => {
    expect(
      toGroupEventData({
        group_id: 'g1',
        user_id: 'u2',
        user_email: 'u2@example.com',
      }),
    ).toEqual({
      groupId: 'g1',
      userId: 'u2',
      userEmail: 'u2@example.com',
    })
  })

  it('forwards values verbatim and forwards unknown keys (still camelCased)', () => {
    expect(
      toGroupEventData({
        group_id: 'g1',
        future_field_we_havent_seen: 'whatever',
        nested: { kept_as_is: true },
      }),
    ).toEqual({
      groupId: 'g1',
      futureFieldWeHaventSeen: 'whatever',
      nested: { kept_as_is: true }, // we don't recurse — server can flatten if needed
    })
  })
})
