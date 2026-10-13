import {
  getNotificationPreferencesNotificationsPreferencesGet,
  updateNotificationPreferencesNotificationsPreferencesPut,
} from '@/client/sdk.gen'
import type { NotificationPreferencesResponse } from '@/client/types.gen'
import type { NotificationPreferencesRepository } from '@/application/ports/NotificationPreferencesRepository'
import type { NotificationPreferences } from '@/domain/notification/NotificationPreferences'
import { NotificationDomainError } from '@/domain/notification/errors'

/**
 * Backend adapter for NotificationPreferencesRepository. Maps the
 * snake_case DTO of /notifications/preferences into the domain shape.
 * Only @/client touchpoint for the notification context.
 */
export class BackendNotificationPreferencesRepository implements NotificationPreferencesRepository {
  async get(): Promise<NotificationPreferences> {
    const response = await getNotificationPreferencesNotificationsPreferencesGet()
    return toDomain(response.data, response.error)
  }

  async update(preferences: NotificationPreferences): Promise<NotificationPreferences> {
    const response = await updateNotificationPreferencesNotificationsPreferencesPut({
      body: {
        notify_on_vault_lock: preferences.notifyOnVaultLock,
        notify_on_vault_unlock: preferences.notifyOnVaultUnlock,
      },
    })
    return toDomain(response.data, response.error)
  }
}

function toDomain(
  data: NotificationPreferencesResponse | undefined,
  error: unknown,
): NotificationPreferences {
  if (error || !data) {
    throw new NotificationDomainError(
      extractDetail(error) ?? 'Notification preferences unavailable',
    )
  }
  return {
    notifyOnVaultLock: data.notify_on_vault_lock,
    notifyOnVaultUnlock: data.notify_on_vault_unlock,
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
