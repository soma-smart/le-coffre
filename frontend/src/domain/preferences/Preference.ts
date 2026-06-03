/**
 * User preferences live behind the PreferencesGateway port. This file
 * declares the keys we know about so call sites don't sprinkle magic
 * strings — the typed `PreferenceKey` keeps refactors safe.
 *
 * Pure TypeScript. No Vue, no SDK, no storage backend.
 */

export const PREFERENCE_KEYS = {
  /** Theme picker bundle: primary color, surface color, dark mode, ripple, preset. */
  THEME_SETTINGS: 'app-settings',
  /** Admin "see every group" toggle on the passwords page. */
  ADMIN_PASSWORD_VIEW_ENABLED: 'admin-password-view-enabled',
} as const

export type PreferenceKey = (typeof PREFERENCE_KEYS)[keyof typeof PREFERENCE_KEYS]
