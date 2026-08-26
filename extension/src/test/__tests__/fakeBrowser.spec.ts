import { describe, expect, it } from 'vitest'

import { createFakeBrowser } from '../fakeBrowser'

// The fake is load-bearing: every handler test in M7+ runs against it, so a
// divergence from the real chrome.* semantics would silently invalidate them.
// These tests pin the behaviours that are easy to get wrong.
describe('createFakeBrowser', () => {
  it('returns undefined for a key that was never set', async () => {
    const browser = createFakeBrowser()

    await expect(browser.local.get('missing')).resolves.toBeUndefined()
  })

  it('serialises stored values, as chrome.storage does', async () => {
    const browser = createFakeBrowser()
    const stored = { nested: { count: 1 } }

    await browser.local.set('key', stored)
    const read = await browser.local.get<typeof stored>('key')

    expect(read).toEqual(stored)
    // Identity must NOT survive: a handler that mutates what it read from
    // storage would appear to work against a naive fake and fail in Chrome.
    expect(read).not.toBe(stored)
  })

  it('keeps local and session isolated from each other', async () => {
    const browser = createFakeBrowser()

    await browser.local.set('token', 'in-local')

    await expect(browser.session.get('token')).resolves.toBeUndefined()
  })

  it('grants requested origins only when the user accepts', async () => {
    const browser = createFakeBrowser()
    browser.grantPermissions = false

    await expect(browser.permissions.request(['https://vault.example.com/api/*'])).resolves.toBe(
      false,
    )
    await expect(browser.permissions.contains(['https://vault.example.com/api/*'])).resolves.toBe(
      false,
    )

    browser.grantPermissions = true
    await expect(browser.permissions.request(['https://vault.example.com/api/*'])).resolves.toBe(
      true,
    )
    await expect(browser.permissions.contains(['https://vault.example.com/api/*'])).resolves.toBe(
      true,
    )
  })

  it('reports contains() false unless every origin is granted', async () => {
    const browser = createFakeBrowser()
    await browser.permissions.request(['https://a.example/api/*'])

    await expect(
      browser.permissions.contains(['https://a.example/api/*', 'https://b.example/api/*']),
    ).resolves.toBe(false)
  })

  it('notifies onRemoved listeners when the user revokes access', async () => {
    const browser = createFakeBrowser()
    let notified = false
    browser.permissions.onRemoved(() => {
      notified = true
    })

    await browser.permissions.request(['https://vault.example.com/api/*'])
    browser.revokePermissions()

    expect(notified).toBe(true)
    await expect(browser.permissions.contains(['https://vault.example.com/api/*'])).resolves.toBe(
      false,
    )
  })

  it('records scheduled alarms and fires them on demand', async () => {
    const browser = createFakeBrowser()
    const fired: string[] = []
    browser.alarms.onAlarm((name) => fired.push(name))

    await browser.alarms.schedule('auto-lock', 1)
    expect(browser.scheduledAlarms.get('auto-lock')).toBe(1)

    browser.triggerAlarm('auto-lock')
    expect(fired).toEqual(['auto-lock'])

    await browser.alarms.clear('auto-lock')
    expect(browser.scheduledAlarms.has('auto-lock')).toBe(false)
  })

  it('records opened tabs', async () => {
    const browser = createFakeBrowser()

    await browser.tabs.create('https://vault.example.com/passwords/Marketing?create=1')

    expect(browser.openedTabs).toEqual(['https://vault.example.com/passwords/Marketing?create=1'])
  })
})
