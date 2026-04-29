import type { GroupRepository } from '@/application/ports/GroupRepository'
import { GroupNameRequiredError } from '@/domain/group/errors'

export interface CreateGroupCommand {
  name: string
}

export class CreateGroupUseCase {
  constructor(private readonly repository: GroupRepository) {}

  async execute(command: CreateGroupCommand): Promise<string> {
    if (!command.name.trim()) throw new GroupNameRequiredError()
    return this.repository.create(command.name.trim())
  }
}
