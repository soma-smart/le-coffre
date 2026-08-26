/**
 * The extension's only view of the browser API.
 *
 * Everything outside `src/platform/chrome/` talks to this interface, never to
 * `chrome.*` directly, enforced by `no-restricted-globals` in eslint.config.ts
 * and by scripts/check-architecture.sh. Two payoffs:
 *
 *  - Firefox is a second adapter rather than a rewrite. (Its `browser.*` API is
 *    promise-based and mostly congruent; the real gaps are `offscreen`, which it
 *    lacks entirely, and MV3 background pages vs service workers.)
 *  - Tests inject `test/fakeBrowser.ts` and never stub a global.
 *
 * Keep this surface small. Every method added here is API an adapter must
 * implement for every browser we support.
 */

export interface StorageArea {
  get<T = unknown>(key: string): Promise<T | undefined>
  set(key: string, value: unknown): Promise<void>
  remove(key: string): Promise<void>
  clear(): Promise<void>
}

export interface Browser {
  /** Persists to disk, survives browser restart. Never put secrets here. */
  readonly local: StorageArea
  /**
   * Memory-backed, cleared when the browser closes, unreadable from content
   * scripts. Survives service-worker restarts, which plain module state does
   * not, MV3 kills the worker after ~30s idle.
   */
  readonly session: StorageArea

  readonly permissions: {
    contains(origins: string[]): Promise<boolean>
    /**
     * MUST be called synchronously inside a user gesture. Any `await` before
     * this call consumes the gesture and Chrome rejects with
     * "This function must be called during a user gesture".
     */
    request(origins: string[]): Promise<boolean>
    remove(origins: string[]): Promise<boolean>
    onRemoved(listener: () => void): void
  }

  readonly tabs: {
    create(url: string): Promise<void>
  }

  readonly alarms: {
    schedule(name: string, periodInMinutes: number): Promise<void>
    clear(name: string): Promise<void>
    onAlarm(listener: (name: string) => void): void
  }

  readonly runtime: {
    /** Absolute URL for a path inside the extension bundle. */
    getUrl(path: string): string
    sendMessage<T = unknown>(message: unknown): Promise<T>
    onMessage(handler: (message: unknown) => Promise<unknown>): void
  }
}
