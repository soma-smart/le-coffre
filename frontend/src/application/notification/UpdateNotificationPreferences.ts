import type { NotificationPreferencesRepository } from '@/application/ports/NotificationPreferencesRepository'
import type { NotificationPreferences } from '@/domain/notification/NotificationPreferences'

export class UpdateNotificationPreferencesUseCase {
  constructor(private readonly repository: NotificationPreferencesRepository) {}

  execute(preferences: NotificationPreferences): Promise<NotificationPreferences> {
    return this.repository.update(preferences)
  }
}
