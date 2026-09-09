/**
 * Carries the browser-extension pairing code across the sign-in round trip.
 *
 * A port of its own rather than a PreferencesGateway key, because the lifetime
 * is the point: the code must not survive the browser session, and it is not a
 * preference. The production adapter is session-scoped for exactly that reason.
 *
 * Why it has to be carried at all: the code arrives in the URL fragment, and
 * the sign-in redirect deliberately carries no fragment. The router guard
 * redirects with `redirect=to.fullPath`, so putting the code in the query
 * string would write it into the SPA host's access log.
 */
export interface PairingHandoffGateway {
  rememberPairingCode(userCode: string): void

  recallPairingCode(): string | null

  forgetPairingCode(): void
}
