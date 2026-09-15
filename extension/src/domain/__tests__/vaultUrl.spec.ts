import { describe, expect, it } from 'vitest'

import {
  isInsecureVaultUrl,
  normalizeVaultUrl,
  toApiMatchPattern,
  toApiUrl,
  toCreatePasswordLink,
  toEditPasswordLink,
  toPairingApprovalLink,
} from '../vaultUrl'

describe('normalizeVaultUrl', () => {
  it('assumes https for a bare host, which is what people type', () => {
    expect(normalizeVaultUrl('vault.example.com')).toBe('https://vault.example.com')
  })

  it('collapses the ways one vault can be typed into a single value', () => {
    // One stored value means one granted permission, instead of a new prompt
    // every time the user types the trailing slash differently.
    for (const typed of [
      'https://vault.example.com',
      'https://vault.example.com/',
      'https://vault.example.com///',
      '  https://vault.example.com  ',
    ]) {
      expect(normalizeVaultUrl(typed)).toBe('https://vault.example.com')
    }
  })

  it('keeps a path prefix for a vault hosted under a sub-path', () => {
    expect(normalizeVaultUrl('https://intranet.example/coffre/')).toBe(
      'https://intranet.example/coffre',
    )
  })

  it('keeps a non-default port', () => {
    expect(normalizeVaultUrl('http://127.0.0.1:8123')).toBe('http://127.0.0.1:8123')
  })

  it('drops query and fragment', () => {
    expect(normalizeVaultUrl('https://vault.example.com/?a=1#x')).toBe('https://vault.example.com')
  })

  it.each(['javascript:alert(1)', 'data:text/html,x', 'file:///etc/passwd', 'ftp://host'])(
    'refuses %s',
    (hostile) => {
      // This value later reaches chrome.tabs.create. Anything but http(s) would
      // turn a stored setting into an arbitrary-navigation primitive.
      expect(normalizeVaultUrl(hostile)).toBeNull()
    },
  )

  it.each(['', '   ', null, undefined])('refuses empty input %s', (empty) => {
    expect(normalizeVaultUrl(empty)).toBeNull()
  })
})

describe('isInsecureVaultUrl', () => {
  it('flags plain http so the UI can warn', () => {
    expect(isInsecureVaultUrl('http://homelab.local')).toBe(true)
    expect(isInsecureVaultUrl('https://vault.example.com')).toBe(false)
  })
})

describe('toApiMatchPattern', () => {
  it('asks only for the API path, not the whole site', () => {
    // The difference between a prompt naming one path and one naming a site.
    expect(toApiMatchPattern('https://vault.example.com')).toBe('https://vault.example.com/api/*')
  })

  it('keeps a sub-path deployment inside its prefix', () => {
    expect(toApiMatchPattern('https://intranet.example/coffre')).toBe(
      'https://intranet.example/coffre/api/*',
    )
  })

  it('refuses to build a pattern from an unusable url', () => {
    expect(toApiMatchPattern('javascript:alert(1)')).toBeNull()
  })
})

describe('toApiUrl', () => {
  it('builds an absolute api url', () => {
    expect(toApiUrl('https://vault.example.com', '/passwords/list')).toBe(
      'https://vault.example.com/api/passwords/list',
    )
  })

  it('tolerates a path without a leading slash', () => {
    expect(toApiUrl('https://vault.example.com', 'health')).toBe(
      'https://vault.example.com/api/health',
    )
  })
})

describe('deep links', () => {
  it('puts the pairing code in the fragment, never the query', () => {
    // The fragment is never sent to the server, so the code cannot reach an
    // access log on the way to /login.
    const link = toPairingApprovalLink('https://vault.example.com', 'K7QM-3XR9')

    expect(link).toBe('https://vault.example.com/extension/connect#code=K7QM-3XR9')
    expect(link).not.toContain('?')
  })

  it('builds the create link from the group name', () => {
    // slugifyGroupName in the web app is currently the identity function. If
    // that ever changes, this test is what flags the coupling instead of a user
    // reporting that Add opens the wrong group.
    expect(toCreatePasswordLink('https://vault.example.com', 'Marketing')).toBe(
      'https://vault.example.com/passwords/Marketing?create=1',
    )
  })

  it('encodes a group name with spaces and slashes', () => {
    expect(toCreatePasswordLink('https://vault.example.com', 'R&D / Ops')).toBe(
      'https://vault.example.com/passwords/R%26D%20%2F%20Ops?create=1',
    )
  })

  it('builds the edit link', () => {
    expect(toEditPasswordLink('https://vault.example.com', 'Marketing', 'abc-123')).toBe(
      'https://vault.example.com/passwords/Marketing?edit=abc-123',
    )
  })

  it('refuses to build a link from an unusable stored url', () => {
    // Guards against a tampered storage value becoming a tab-open primitive.
    expect(toPairingApprovalLink('javascript:alert(1)', 'K7QM-3XR9')).toBeNull()
    expect(toCreatePasswordLink('', 'Marketing')).toBeNull()
  })
})
