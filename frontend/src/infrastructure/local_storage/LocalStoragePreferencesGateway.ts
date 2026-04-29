import type { PreferencesGateway } from '@/application/ports/PreferencesGateway'
import type { PreferenceKey } from '@/domain/preferences/Preference'

/**
 * Production PreferencesGateway backed by `window.localStorage`. JSON-encodes
 * non-string values so callers can stash typed bundles. A corrupted entry
 * (manual tampering, Safari private mode, schema drift) returns `null` rather
 * than throwing — preferences are non-load-bearing UX state, the app should
 * keep running with defaults.
 *
 * This is the *only* place in the codebase that calls `localStorage` for
 * preference data. Everything else routes through the port via use cases.
 */
export class LocalStoragePreferencesGateway implements PreferencesGateway {
  read<T>(key: PreferenceKey): T | null {
    try {
      const raw = window.localStorage.getItem(key)
      if (raw === null) return null
      return JSON.parse(raw) as T
    } catch {
      return null
    }
  }

  write<T>(key: PreferenceKey, value: T): void {
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // Quota exceeded, private mode, etc. — silently ignore; preferences
      // are non-essential.
    }
  }

  remove(key: PreferenceKey): void {
    try {
      window.localStorage.removeItem(key)
    } catch {
      // Same as above.
    }
  }
}
