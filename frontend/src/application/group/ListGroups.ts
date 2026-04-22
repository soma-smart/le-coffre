import type { Group } from '@/domain/group/Group'
import type { GroupRepository } from '@/application/ports/GroupRepository'

export interface ListGroupsCommand {
  /** Default: true — include both personal and shared groups. */
  includePersonal?: boolean
}

export class ListGroupsUseCase {
  constructor(private readonly repository: GroupRepository) {}

  execute(command: ListGroupsCommand = {}): Promise<Group[]> {
    return this.repository.list({ includePersonal: command.includePersonal ?? true })
  }
}
