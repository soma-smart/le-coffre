/**
 * Carries the post-login destination across the SSO round trip.
 *
 * The password flow keeps `?redirect=` in the URL the whole way, but the SSO
 * flow leaves the app entirely: window.location goes to the identity provider
 * and comes back on /sso/callback, where the router query is whatever the
 * provider sent. Pinia does not survive that unload; session storage does,
 * and dies with the tab, which is exactly the lifetime a handoff needs.
 */
export interface LoginRedirectGateway {
  remember(path: string): void

  /** Return the stored destination and forget it, or null when none is held. */
  consume(): string | null
}
