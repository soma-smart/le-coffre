/**
 * A destination the SPA may router.push after login.
 *
 * In-app paths only: one leading slash (so no protocol-relative "//evil.com"),
 * and no scheme separator anywhere. Everything else is refused rather than
 * sanitised, because a login redirect is the classic open-redirect vehicle.
 */
export function isSafeInternalPath(path: string): boolean {
  return path.startsWith('/') && !path.startsWith('//') && !path.includes('://')
}
