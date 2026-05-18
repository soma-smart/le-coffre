import type { GroupRepository } from '@/application/ports/GroupRepository'
import { GroupUserRequiredError } from '@/domain/group/errors'

export interface AddMemberToGroupCommand {
  groupId: string
  userId: string
}

export class AddMemberToGroupUseCase {
  constructor(private readonly repository: GroupRepository) {}

  async execute(command: AddMemberToGroupCommand): Promise<void> {
    if (!command.userId) throw new GroupUserRequiredError()
    await this.repository.addMember(command.groupId, command.userId)
  }
}
