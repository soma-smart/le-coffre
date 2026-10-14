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

  it('never crosses schemes', () => {
    // On http the page can be anyone on the network. An entry saved for the
    // https site must not be offered there, and the reverse hides nothing
    // worth having.
    expect(matchesDomain('https://intranet.example', 'http://intranet.example/login')).toBe('none')
    expect(matchesDomain('http://intranet.example', 'https://intranet.example/login')).toBe('none')
  })

  it('needs the ports to agree when one is given', () => {
    // Two services on one host are two services.
    expect(matchesDomain('https://host.example:8443', 'https://host.example/')).toBe('none')
    expect(matchesDomain('https://host.example', 'https://host.example:8443/')).toBe('none')
    expect(matchesDomain('https://host.example:8443', 'https://host.example:8443/x')).toBe('host')
  })

  it('treats the default port as no port', () => {
    expect(matchesDomain('https://host.example:443', 'https://host.example/x')).toBe('host')
  })

  it('takes a scheme-less entry to be https', () => {
    // What older rows look like: `github.com`, typed without a scheme.
    expect(matchesDomain('github.com', 'https://github.com/login')).toBe('host')
    expect(matchesDomain('github.com', 'http://github.com/login')).toBe('none')
    expect(matchesDomain('github.com/login', 'https://github.com/login')).toBe('exact')
  })

  it('KNOWN LIMITATION: an entry that is itself a public suffix matches every site under it', () => {
    // Pinned, not endorsed. Without the Public Suffix List, `github.io` is a
    // parent of `evil.github.io` exactly as `example.com` is a parent of
    // `mail.example.com`. Nothing calls this yet; the autofill work decides.
    expect(matchesDomain('https://github.io', 'https://evil.github.io/login')).toBe('parent-domain')
  })

  it('KNOWN LIMITATION: the symmetric branch offers a subdomain entry on its public suffix', () => {
    expect(matchesDomain('https://me.github.io', 'https://github.io/')).toBe('parent-domain')
  })

  it.each(['javascript:alert(1)', 'data:text/html,x', 'file:///etc/passwd', 'not a url'])(
    'refuses %s',
    (hostile) => {
      expect(matchesDomain(hostile, 'https://github.com')).toBe('none')
      expect(matchesDomain('https://github.com', hostile)).toBe('none')
    },
  )
})
