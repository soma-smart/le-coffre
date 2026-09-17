import type { GroupEvent } from '@/domain/group/Group'
import type { GroupRepository } from '@/application/ports/GroupRepository'

export interface ListGroupEventsCommand {
  groupId: string
  eventTypes?: string[]
  startDate?: string
  endDate?: string
}

/**
 * Membership-history reader for a group. Supports optional event-type and
 * date-range filters that the history modal uses, mirroring
 * ListPasswordEventsUseCase. Pushes filters down to the repository so every
 * implementation (backend HTTP, in-memory) can do the narrowing closest to
 * the data.
 */
export class ListGroupEventsUseCase {
  constructor(private readonly repository: GroupRepository) {}

  execute(command: ListGroupEventsCommand): Promise<GroupEvent[]> {
    return this.repository.listEvents(command.groupId, {
      eventTypes: command.eventTypes,
      startDate: command.startDate,
      endDate: command.endDate,
    })
  }
}
