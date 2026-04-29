import type { GroupRepository } from '@/application/ports/GroupRepository'
import { GroupUserRequiredError } from '@/domain/group/errors'

export interface PromoteMemberToOwnerCommand {
  groupId: string
  userId: string
}

export class PromoteMemberToOwnerUseCase {
  constructor(private readonly repository: GroupRepository) {}

  async execute(command: PromoteMemberToOwnerCommand): Promise<void> {
    if (!command.userId) throw new GroupUserRequiredError()
    await this.repository.promoteToOwner(command.groupId, command.userId)
  }
}
