import type { Group } from '@/domain/group/Group'
import type { GroupRepository } from '@/application/ports/GroupRepository'

export interface GetGroupCommand {
  groupId: string
}

export class GetGroupUseCase {
  constructor(private readonly repository: GroupRepository) {}

  execute(command: GetGroupCommand): Promise<Group> {
    return this.repository.get(command.groupId)
  }
}
