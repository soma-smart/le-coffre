import { describe, expect, it } from 'vitest'

import type { Entry } from '@/domain/entry'
import type { Group } from '@/domain/group'

import { copyToClipboard } from '../handlers/clipboard'
import { listEntries, listGroups, selectGroup } from '../handlers/vault'
import { createTestDeps, givenPaired } from './testDeps'

function group(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Marketing',
    isPersonal: false,
    isOwner: false,
    ...overrides,
  }
}

function entry(overrides: Partial<Entry> = {}): Entry {
  return {
    id: 'e1',
    name: 'Production database',
    folder: 'infra',
    login: 'dba',
    url: 'https://db.example.com',
    groupId: 'g1',
    accessibleGroupIds: [],
    canRead: true,
    canWrite: true,
    accessExpiresAt: null,
    ...overrides,
  }
}

describe('listGroups', () => {
  it('should pass through what the server scoped, personal group first', async () => {
    // Scoping moved to the server: /extension/groups applies the owner-or-member
    // rule itself, so a token in browser storage cannot enumerate the instance.
    // The backend owns that guarantee now: see test_list_groups_use_case.py.
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.groupsResult = {
      ok: true,
      data: [
        group({ id: 'shared', name: 'Marketing' }),
        group({ id: 'personal', name: 'Alice', isPersonal: true }),
      ],
    }

    const result = await listGroups(deps)

    expect(result.ok && result.data.map((g) => g.id)).toEqual(['personal', 'shared'])
  })

  it('should mark the groups the user owns, since only owners can add', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.groupsResult = { ok: true, data: [group({ id: 'owned', isOwner: true })] }

    const result = await listGroups(deps)

    expect(result.ok && result.data[0].isOwner).toBe(true)
  })
})

describe('listEntries', () => {
  it('should keep an entry shared into the selected group', async () => {
    // Filtering on groupId alone would make every shared entry vanish here
    // while it stays visible in the web app.
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.entriesResult = {
      ok: true,
      data: [entry({ groupId: 'elsewhere', accessibleGroupIds: ['elsewhere', 'mine'] })],
    }

    const result = await listEntries(deps, 'mine')

    expect(result.ok && result.data.entries).toHaveLength(1)
  })

  it('should hide unreadable entries and say how many', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.entriesResult = {
      ok: true,
      data: [
        entry({ id: 'ok', groupId: 'mine' }),
        entry({ id: 'no', groupId: 'mine', canRead: false }),
      ],
    }

    const result = await listEntries(deps, 'mine')

    expect(result.ok && result.data.entries.map((e) => e.id)).toEqual(['ok'])
    expect(result.ok && result.data.hiddenCount).toBe(1)
  })

  it('should never carry a secret in the listing', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.entriesResult = { ok: true, data: [entry({ groupId: 'mine' })] }

    const result = await listEntries(deps, 'mine')

    const listed = result.ok ? result.data.entries[0] : null
    expect(listed).not.toHaveProperty('password')
    expect(client.revealCalls).toEqual([])
  })

  it('should apply the search query', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.entriesResult = {
      ok: true,
      data: [
        entry({ id: 'db', name: 'Production database', groupId: 'mine' }),
        entry({ id: 'mail', name: 'Mailbox', groupId: 'mine' }),
      ],
    }

    const result = await listEntries(deps, 'mine', 'mail')

    expect(result.ok && result.data.entries.map((e) => e.id)).toEqual(['mail'])
  })
})

describe('selectGroup', () => {
  it('should remember the choice and drop the stale cache', async () => {
    // The cache was filtered for the previous group.
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)
    await browser.session.set('entriesCache', { entries: [], cachedAt: 'x' })

    await selectGroup(deps, 'chosen')

    await expect(browser.local.get('selectedGroupId')).resolves.toBe('chosen')
    await expect(browser.session.get('entriesCache')).resolves.toBeUndefined()
  })
})

describe('copyToClipboard', () => {
  it('should fetch a password only when asked, never ahead of time', async () => {
    // Every fetch writes a PasswordAccessedEvent in the vault's audit log.
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.entriesResult = { ok: true, data: [entry({ id: 'e1', groupId: 'mine' })] }
    client.revealResult = { ok: true, data: 's3cret' }

    await listEntries(deps, 'mine')
    expect(client.revealCalls).toEqual([])

    await copyToClipboard(deps, 'e1', 'password')
    expect(client.revealCalls).toEqual(['e1'])
  })

  it('should hand the secret to the clipboard with a clear timeout', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.revealResult = { ok: true, data: 's3cret' }

    const result = await copyToClipboard(deps, 'e1', 'password')

    expect(browser.clipboardWrites).toEqual([{ value: 's3cret', clearAfterSeconds: 30 }])
    expect(result.ok && result.data.clearsInSeconds).toBe(30)
  })

  it('should copy a login from the cache without touching the network', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.entriesResult = { ok: true, data: [entry({ id: 'e1', groupId: 'mine', login: 'dba' })] }
    await listEntries(deps, 'mine')

    await copyToClipboard(deps, 'e1', 'login')

    expect(browser.clipboardWrites[0].value).toBe('dba')
    expect(client.revealCalls).toEqual([])
  })

  it('should report a failure rather than hand the secret back to the popup', async () => {
    // Returning the value for the popup to copy would put a live secret in the
    // Vue tree, which is the one thing this whole path exists to avoid.
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.revealResult = { ok: true, data: 's3cret' }
    browser.clipboardAvailable = false

    const result = await copyToClipboard(deps, 'e1', 'password')

    expect(result).toEqual({ ok: false, error: { kind: 'CLIPBOARD_UNAVAILABLE' } })
    expect(JSON.stringify(result)).not.toContain('s3cret')
  })
})
