import type { NotificationPreferencesRepository } from '@/application/ports/NotificationPreferencesRepository'
import type { NotificationPreferences } from '@/domain/notification/NotificationPreferences'

export class GetNotificationPreferencesUseCase {
  constructor(private readonly repository: NotificationPreferencesRepository) {}

  execute(): Promise<NotificationPreferences> {
    return this.repository.get()
  }
}
