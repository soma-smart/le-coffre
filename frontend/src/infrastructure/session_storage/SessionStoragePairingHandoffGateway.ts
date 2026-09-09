import type { PairingHandoffGateway } from '@/application/ports/PairingHandoffGateway'

const PAIRING_CODE_KEY = 'extension-pairing-code'

/**
 * Production PairingHandoffGateway backed by `window.sessionStorage`.
 *
 * Session-scoped on purpose: the code is a short-lived handoff, and a value
 * that outlived the tab would mean a stale approval page could be reopened
 * later against a pairing the user has forgotten starting.
 *
 * Every access is guarded: sessionStorage throws in some privacy modes, and a
 * pairing flow should degrade to "no code supplied" rather than a blank page.
 */
export class SessionStoragePairingHandoffGateway implements PairingHandoffGateway {
  rememberPairingCode(userCode: string): void {
    try {
      window.sessionStorage.setItem(PAIRING_CODE_KEY, userCode)
    } catch {
      // Private mode or a full quota. The in-page flow still works; only the
      // sign-in round trip loses the code.
    }
  }

  recallPairingCode(): string | null {
    try {
      return window.sessionStorage.getItem(PAIRING_CODE_KEY)
    } catch {
      return null
    }
  }

  forgetPairingCode(): void {
    try {
      window.sessionStorage.removeItem(PAIRING_CODE_KEY)
    } catch {
      // Nothing to recover from: the value dies with the session anyway.
    }
  }
}
