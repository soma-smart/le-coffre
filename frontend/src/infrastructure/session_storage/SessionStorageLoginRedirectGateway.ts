import type { LoginRedirectGateway } from '@/application/ports/LoginRedirectGateway'

const LOGIN_REDIRECT_KEY = 'login-redirect-path'

/**
 * Production LoginRedirectGateway backed by `window.sessionStorage`.
 *
 * Guarded like its pairing sibling: sessionStorage throws in some privacy
 * modes, and losing the redirect must degrade to "land on the home page",
 * never to a blank page.
 */
export class SessionStorageLoginRedirectGateway implements LoginRedirectGateway {
  remember(path: string): void {
    try {
      window.sessionStorage.setItem(LOGIN_REDIRECT_KEY, path)
    } catch {
      // Losing the handoff only costs the user one extra navigation.
    }
  }

  consume(): string | null {
    try {
      const path = window.sessionStorage.getItem(LOGIN_REDIRECT_KEY)
      window.sessionStorage.removeItem(LOGIN_REDIRECT_KEY)
      return path
    } catch {
      return null
    }
  }
}
