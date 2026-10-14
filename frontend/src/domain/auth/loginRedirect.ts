/**
 * A destination the SPA may router.push after login.
 *
 * In-app paths only. Everything else is refused rather than sanitised, because
 * a login redirect is the classic open-redirect vehicle.
 *
 * The obvious rule, "one leading slash and no scheme", was not enough. The
 * router hands the path to history.pushState, and the browser parses it with
 * the WHATWG URL rules: a backslash counts as a slash, and tabs and newlines
 * are stripped before parsing. So "/\evil.com" and "/\t/evil.com" both become
 * "//evil.com", pushState rejects the cross-origin result, and vue-router
 * falls back to location.assign, which leaves the site. Hence three checks:
 *
 *   - no backslash, no control character, no whitespace, anywhere;
 *   - one leading slash, not two;
 *   - the path resolved against a fixed origin must stay on that origin, which
 *     catches whatever else the URL parser would turn into a host.
 *
 * "/%5Cevil.com" passes: the backslash is percent-encoded, so the parser keeps
 * it as a path segment and the page stays on the origin.
 */
export function isSafeInternalPath(path: string): boolean {
  if (/[\\\s\u0000-\u001f\u007f]/.test(path)) return false
  if (!path.startsWith('/') || path.startsWith('//')) return false

  try {
    return new URL(path, 'http://redirect.invalid').origin === 'http://redirect.invalid'
  } catch {
    return false
  }
}

/**
 * Normalise a redirect value read from outside the app (the URL query, session
 * storage) into a safe path, or null.
 *
 * `unknown` on purpose: a repeated `?redirect=` reaches the router as an array,
 * and the callers used to cast it to a string and `.trim()` it.
 */
export function toLoginRedirect(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const path = value.trim()
  if (!path || !isSafeInternalPath(path)) return null
  return path
}
