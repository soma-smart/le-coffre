import type { UserPasswordEvent } from '@/domain/user/User'
import type {
  ListUserPasswordEventsFilters,
  UserRepository,
} from '@/application/ports/UserRepository'

export interface ListUserPasswordEventsCommand {
  userId: string
  eventTypes?: string[]
  startDate?: string
  endDate?: string
}

/**
 * Audit-log reader for a specific actor (user). Supports optional
 * event-type and date-range filters that the admin user-history modal uses.
 */
export class ListUserPasswordEventsUseCase {
  constructor(private readonly repository: UserRepository) {}

  execute(command: ListUserPasswordEventsCommand): Promise<UserPasswordEvent[]> {
    const filters: ListUserPasswordEventsFilters = {
      eventTypes: command.eventTypes,
      startDate: command.startDate,
      endDate: command.endDate,
    }
    return this.repository.listPasswordEvents(command.userId, filters)
  }
}
