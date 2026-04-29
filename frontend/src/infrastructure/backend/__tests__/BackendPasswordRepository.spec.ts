import { describe, expect, it } from 'vitest'
import { toPasswordEventData } from '@/infrastructure/backend/BackendPasswordRepository'

describe('toPasswordEventData', () => {
  it('returns an empty object for null / undefined / non-object input', () => {
    expect(toPasswordEventData(null)).toEqual({})
    expect(toPasswordEventData(undefined)).toEqual({})
    expect(toPasswordEventData('not an object')).toEqual({})
    expect(toPasswordEventData(42)).toEqual({})
  })

  it('camelCases the keys we know about for share / unshare events', () => {
    expect(
      toPasswordEventData({
        shared_with_group_id: 'g1',
        shared_with_group_name: 'Engineering',
      }),
    ).toEqual({
      sharedWithGroupId: 'g1',
      sharedWithGroupName: 'Engineering',
    })

    expect(
      toPasswordEventData({
        unshared_with_group_id: 'g2',
        unshared_with_group_name: 'Legacy',
      }),
    ).toEqual({
      unsharedWithGroupId: 'g2',
      unsharedWithGroupName: 'Legacy',
    })
  })

  it('camelCases the boolean flags emitted by update events', () => {
    expect(
      toPasswordEventData({
        has_name_changed: true,
        has_password_changed: true,
        has_folder_changed: false,
        has_login_changed: false,
        has_url_changed: false,
      }),
    ).toEqual({
      hasNameChanged: true,
      hasPasswordChanged: true,
      hasFolderChanged: false,
      hasLoginChanged: false,
      hasUrlChanged: false,
    })
  })

  it('forwards values verbatim and forwards unknown keys (still camelCased)', () => {
    expect(
      toPasswordEventData({
        folder: 'Work',
        future_field_we_havent_seen: 'whatever',
        nested: { kept_as_is: true },
      }),
    ).toEqual({
      folder: 'Work',
      futureFieldWeHaventSeen: 'whatever',
      nested: { kept_as_is: true }, // we don't recurse — server can flatten if needed
    })
  })
})
