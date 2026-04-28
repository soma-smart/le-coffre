import type { PreferencesGateway } from '@/application/ports/PreferencesGateway'
import type { PreferenceKey } from '@/domain/preferences/Preference'

/**
 * Map-backed PreferencesGateway used by tests. Stores values verbatim — no
 * JSON serialisation — so a test that writes `{ darkTheme: true }` reads back
 * the same object reference. The production adapter does serialise; the
 * port contract treats both as opaque T.
 */
export class InMemoryPreferencesGateway implements PreferencesGateway {
  private readonly store = new Map<PreferenceKey, unknown>()

  read<T>(key: PreferenceKey): T | null {
    return (this.store.get(key) ?? null) as T | null
  }

  write<T>(key: PreferenceKey, value: T): void {
    this.store.set(key, value)
  }

  remove(key: PreferenceKey): void {
    this.store.delete(key)
  }

  /** Test helper — pre-populate without going through `write()`. */
  seed<T>(key: PreferenceKey, value: T): this {
    this.store.set(key, value)
    return this
  }

  clear(): void {
    this.store.clear()
  }
}
