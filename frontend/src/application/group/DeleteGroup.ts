import type { GroupRepository } from '@/application/ports/GroupRepository'

export interface DeleteGroupCommand {
  groupId: string
}

export class DeleteGroupUseCase {
  constructor(private readonly repository: GroupRepository) {}

  execute(command: DeleteGroupCommand): Promise<void> {
    return this.repository.delete(command.groupId)
  }
}
