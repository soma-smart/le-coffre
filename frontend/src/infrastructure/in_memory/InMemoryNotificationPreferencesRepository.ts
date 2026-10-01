import type { NotificationPreferencesRepository } from '@/application/ports/NotificationPreferencesRepository'
import {
  DEFAULT_NOTIFICATION_PREFERENCES,
  type NotificationPreferences,
} from '@/domain/notification/NotificationPreferences'

/** Test-only implementation of NotificationPreferencesRepository. */
export class InMemoryNotificationPreferencesRepository implements NotificationPreferencesRepository {
  private preferences: NotificationPreferences = { ...DEFAULT_NOTIFICATION_PREFERENCES }
  private updateError: Error | null = null
  private getError: Error | null = null

  seed(preferences: NotificationPreferences): this {
    this.preferences = { ...preferences }
    return this
  }

  /** Force the next update() call to throw — for testing error paths. */
  failUpdateOnce(error: Error): this {
    this.updateError = error
    return this
  }

  /** Force the next get() call to throw — for testing error paths. */
  failGetOnce(error: Error): this {
    this.getError = error
    return this
  }

  async get(): Promise<NotificationPreferences> {
    if (this.getError) {
      const e = this.getError
      this.getError = null
      throw e
    }
    return { ...this.preferences }
  }

  async update(preferences: NotificationPreferences): Promise<NotificationPreferences> {
    if (this.updateError) {
      const e = this.updateError
      this.updateError = null
      throw e
    }
    this.preferences = { ...preferences }
    return { ...this.preferences }
  }
}
