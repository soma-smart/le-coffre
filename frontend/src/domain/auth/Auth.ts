/**
 * Auth domain types. Pure TypeScript — no Vue, no fetch, no SDK.
 *
 * The auth context has no persistent entities on the frontend — cookies
 * hold the session. The only domain type worth promoting is the
 * SSO-callback payload, because the page that handles it needs to
 * display greet-the-user state decided on the server (isNewUser +
 * displayName).
 */

export interface SsoUserInfo {
  userId: string
  email: string
  displayName: string
  isNewUser: boolean
}

export interface SsoCallbackResult {
  user: SsoUserInfo
}
