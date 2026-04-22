import type { PasswordEvent } from '@/domain/password/Password'
import type { PasswordRepository } from '@/application/ports/PasswordRepository'

export interface ListPasswordEventsCommand {
  passwordId: string
  eventTypes?: string[]
  startDate?: string
  endDate?: string
}

/**
 * Audit-log reader. Supports optional event-type and date-range filters
 * that the history modal uses. Pushes filters down to the repository so
 * every implementation (backend HTTP, in-memory) can do the narrowing
 * closest to the data.
 */
export class ListPasswordEventsUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  execute(command: ListPasswordEventsCommand): Promise<PasswordEvent[]> {
    return this.repository.listEvents(command.passwordId, {
      eventTypes: command.eventTypes,
      startDate: command.startDate,
      endDate: command.endDate,
    })
  }
}
