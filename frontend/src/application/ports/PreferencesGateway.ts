import type { PreferenceKey } from '@/domain/preferences/Preference'

/**
 * Port for user-preference persistence. The production adapter wraps
 * `localStorage`; the test adapter is a Map. Presentation code never
 * touches the concrete storage backend — it only knows about this port
 * via the use-case wrappers under `application/preferences/`.
 */
export interface PreferencesGateway {
  /**
   * Read a preference by key. Returns `null` if not stored. Implementations
   * MUST swallow JSON parse errors and return `null` rather than throw —
   * a corrupted preference is recoverable, a thrown error is not.
   */
  read<T>(key: PreferenceKey): T | null

  /** Persist a preference. JSON-serialised for non-string values. */
  write<T>(key: PreferenceKey, value: T): void

  /** Remove a preference. No-op if not stored. */
  remove(key: PreferenceKey): void
}
