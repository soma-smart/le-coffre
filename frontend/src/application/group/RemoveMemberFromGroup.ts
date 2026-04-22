import type { GroupRepository } from '@/application/ports/GroupRepository'
import { GroupUserRequiredError } from '@/domain/group/errors'

export interface RemoveMemberFromGroupCommand {
  groupId: string
  userId: string
}

export class RemoveMemberFromGroupUseCase {
  constructor(private readonly repository: GroupRepository) {}

  async execute(command: RemoveMemberFromGroupCommand): Promise<void> {
    if (!command.userId) throw new GroupUserRequiredError()
    await this.repository.removeMember(command.groupId, command.userId)
  }
}
