/**
 * The CSRF bounded context is small enough that it doesn't need its own
 * domain types — a raw token string is the whole value. The gateway is
 * the only contract the use case cares about.
 */
export interface CsrfGateway {
  fetchToken(): Promise<string>
}
