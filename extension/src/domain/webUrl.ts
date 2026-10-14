/**
 * The one definition of "a web URL": absolute, http or https, nothing else.
 *
 * Shared by the vault URL (vaultUrl.ts), the autofill matcher (matchesDomain.ts)
 * and the entry summary the popup builds its "Open site" button from. Three
 * private parsers would drift, and the one that drifted would be the hole: any
 * value that reaches `tabs.create` unchecked is an arbitrary-navigation
 * primitive, and a vault entry's url is typed by whoever created the entry.
 */
const WEB_PROTOCOLS = new Set(['http:', 'https:'])

/**
 * Parse an absolute http(s) URL, or return null.
 *
 * A relative value (`/login`, `github.com`) has no scheme and is refused with
 * the rest: without a base there is nothing safe to resolve it against.
 */
export function parseWebUrl(value: string | null | undefined): URL | null {
  const trimmed = value?.trim()
  if (!trimmed) return null

  try {
    const url = new URL(trimmed)
    return WEB_PROTOCOLS.has(url.protocol) && !!url.hostname ? url : null
  } catch {
    return null
  }
}

/** The value as something safe to hand to `tabs.create`, or null. */
export function toSafeWebUrl(value: string | null | undefined): string | null {
  return parseWebUrl(value)?.href ?? null
}
