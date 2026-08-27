/**
 * Domain matching for autofill. Written and tested now, unused by the v1 UI.
 *
 * Ranked rather than boolean, because autofill has to order candidates: a
 * boolean would have to be replaced wholesale the moment two entries match.
 *
 * KNOWN LIMITATION: parent-domain matching uses a dot-prefixed suffix, not the
 * Public Suffix List. That means `foo.co.uk` and `bar.co.uk` are treated as
 * sharing a parent, which the PSL would refuse. Bundling the PSL is too heavy
 * for a popup; the autofill work should make that call deliberately rather than
 * inherit it by accident.
 */
export type MatchQuality = 'exact' | 'host' | 'parent-domain' | 'none'

/** Ordering for candidate lists. Higher is a better match. */
export const MATCH_RANK: Record<MatchQuality, number> = {
  exact: 3,
  host: 2,
  'parent-domain': 1,
  none: 0,
}

function parse(value: string | null | undefined): URL | null {
  if (!value) return null
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:' ? url : null
  } catch {
    return null
  }
}

export function matchesDomain(entryUrl: string | null, pageUrl: string): MatchQuality {
  const entry = parse(entryUrl)
  const page = parse(pageUrl)
  if (!entry || !page) return 'none'

  const entryHost = entry.hostname.toLowerCase()
  const pageHost = page.hostname.toLowerCase()

  if (entryHost === pageHost) {
    // Same host: an identical path is a stronger signal than the host alone,
    // which matters for vaults that store several accounts on one site.
    return entry.pathname === page.pathname ? 'exact' : 'host'
  }

  // NEVER a bare endsWith. 'evil-github.com'.endsWith('github.com') is true,
  // which would hand an attacker's page the credentials for the real site.
  // The leading dot is what makes this a subdomain test rather than a
  // substring test.
  if (pageHost.endsWith(`.${entryHost}`) || entryHost.endsWith(`.${pageHost}`)) {
    return 'parent-domain'
  }

  return 'none'
}
