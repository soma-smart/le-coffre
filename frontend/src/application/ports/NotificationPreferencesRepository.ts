import type { NotificationPreferences } from '@/domain/notification/NotificationPreferences'

export interface NotificationPreferencesRepository {
  /** The current user's preferences. */
  get(): Promise<NotificationPreferences>
  /** Replaces the current user's preferences and returns what was stored. */
  update(preferences: NotificationPreferences): Promise<NotificationPreferences>
}
