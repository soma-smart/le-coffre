import type { GroupRepository } from '@/application/ports/GroupRepository'
import { GroupNameRequiredError } from '@/domain/group/errors'

export interface UpdateGroupCommand {
  groupId: string
  name: string
}

export class UpdateGroupUseCase {
  constructor(private readonly repository: GroupRepository) {}

  async execute(command: UpdateGroupCommand): Promise<void> {
    if (!command.name.trim()) throw new GroupNameRequiredError()
    await this.repository.update(command.groupId, command.name.trim())
  }
}
