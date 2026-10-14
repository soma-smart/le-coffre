/**
 * Domain matching for autofill. Written and tested now, unused by the v1 UI.
 *
 * Ranked rather than boolean, because autofill has to order candidates: a
 * boolean would have to be replaced wholesale the moment two entries match.
 *
 * Scheme and port take part in the match, not just the host. An entry saved
 * for `https://intranet` must not be offered on `http://intranet`, where a
 * page can be anyone on the network, and `https://host:8443` is not the same
 * service as `https://host`. An entry with no scheme at all (`github.com`,
 * which older rows carry) is taken to be https.
 *
 * KNOWN LIMITATION: the parent-domain rule is a dot-prefixed suffix test, not
 * the Public Suffix List. The residual is an entry whose host is itself a
 * public suffix: an entry saved for `github.io` matches every site under it,
 * `evil.github.io` included, and the symmetric branch offers an entry saved
 * for `me.github.io` on a page at `github.io`. Bundling the PSL is too heavy
 * for a popup, and nothing calls this yet; the autofill work should make that
 * call deliberately rather than inherit it by accident. Both cases are pinned
 * in matchesDomain.spec.ts so the choice stays visible.
 */
import { parseWebUrl } from './webUrl'

export type MatchQuality = 'exact' | 'host' | 'parent-domain' | 'none'

/** Ordering for candidate lists. Higher is a better match. */
export const MATCH_RANK: Record<MatchQuality, number> = {
  exact: 3,
  host: 2,
  'parent-domain': 1,
  none: 0,
}

/** An entry url may lack its scheme; a page url, coming from the browser, never does. */
function parseEntryUrl(value: string | null): URL | null {
  const trimmed = value?.trim()
  if (!trimmed) return null
  const withScheme = /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(trimmed) ? trimmed : `https://${trimmed}`
  return parseWebUrl(withScheme)
}

export function matchesDomain(entryUrl: string | null, pageUrl: string): MatchQuality {
  const entry = parseEntryUrl(entryUrl)
  const page = parseWebUrl(pageUrl)
  if (!entry || !page) return 'none'

  // `URL.port` is '' for the scheme's default, so `https://a:443` and
  // `https://a` compare equal while `https://a:8443` does not.
  if (entry.protocol !== page.protocol || entry.port !== page.port) return 'none'

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
