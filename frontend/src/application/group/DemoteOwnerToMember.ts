import type { GroupRepository } from '@/application/ports/GroupRepository'
import { GroupUserRequiredError } from '@/domain/group/errors'

export interface DemoteOwnerToMemberCommand {
  groupId: string
  userId: string
}

export class DemoteOwnerToMemberUseCase {
  constructor(private readonly repository: GroupRepository) {}

  async execute(command: DemoteOwnerToMemberCommand): Promise<void> {
    if (!command.userId) throw new GroupUserRequiredError()
    await this.repository.demoteToMember(command.groupId, command.userId)
  }
}
