import { describe, expect, it } from 'vitest'

import { MATCH_RANK, matchesDomain } from '../matchesDomain'

describe('matchesDomain', () => {
  it('never matches a look-alike host', () => {
    // THE test. 'evil-github.com'.endsWith('github.com') is true, so a bare
    // endsWith would hand an attacker's page the real site's credentials.
    expect(matchesDomain('https://github.com', 'https://evil-github.com/login')).toBe('none')
    expect(matchesDomain('https://evil-github.com', 'https://github.com/login')).toBe('none')
  })

  it('matches the same host', () => {
    expect(matchesDomain('https://github.com/login', 'https://github.com/settings')).toBe('host')
  })

  it('ranks an identical path above the host alone', () => {
    // Matters for a vault holding several accounts on one site.
    expect(matchesDomain('https://github.com/login', 'https://github.com/login')).toBe('exact')
    expect(MATCH_RANK.exact).toBeGreaterThan(MATCH_RANK.host)
  })

  it('matches a genuine subdomain', () => {
    expect(matchesDomain('https://example.com', 'https://mail.example.com/inbox')).toBe(
      'parent-domain',
    )
  })

  it('ranks a subdomain below the same host', () => {
    expect(MATCH_RANK.host).toBeGreaterThan(MATCH_RANK['parent-domain'])
  })

  it('is case insensitive on the host', () => {
    expect(matchesDomain('https://GitHub.com', 'https://github.com')).not.toBe('none')
  })

  it('ignores an entry with no url', () => {
    expect(matchesDomain(null, 'https://github.com')).toBe('none')
  })

  it.each(['javascript:alert(1)', 'data:text/html,x', 'file:///etc/passwd', 'not a url'])(
    'refuses %s',
    (hostile) => {
      expect(matchesDomain(hostile, 'https://github.com')).toBe('none')
      expect(matchesDomain('https://github.com', hostile)).toBe('none')
    },
  )
})
