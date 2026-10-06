/**
 * Which optional emails the current user receives. Pure TypeScript — no
 * Vue, no fetch, no SDK. Everything is off until the user turns it on.
 */
export interface NotificationPreferences {
  /** Email when the vault gets locked (by an admin, or by a server restart). */
  notifyOnVaultLock: boolean
  /** Email when the vault gets unlocked. */
  notifyOnVaultUnlock: boolean
}

export const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreferences = {
  notifyOnVaultLock: false,
  notifyOnVaultUnlock: false,
}
