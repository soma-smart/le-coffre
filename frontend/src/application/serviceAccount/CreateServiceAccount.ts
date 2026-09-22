import type { ServiceAccountRepository } from '@/application/ports/ServiceAccountRepository'
import type { CreatedServiceAccount } from '@/domain/serviceAccount/ServiceAccount'
import { validateServiceAccountName } from '@/domain/serviceAccount/ServiceAccount'
import { ServiceAccountGroupRequiredError } from '@/domain/serviceAccount/errors'

export interface CreateServiceAccountCommand {
  groupId: string
  name: string
}

/**
 * Unlike its siblings this use case is not a bare delegator: it normalises and
 * checks the name first, so a blank or over-long one fails here rather than
 * costing a round trip to come back as a 400.
 */
export class CreateServiceAccountUseCase {
  constructor(private readonly repository: ServiceAccountRepository) {}

  async execute(command: CreateServiceAccountCommand): Promise<CreatedServiceAccount> {
    if (!command.groupId) throw new ServiceAccountGroupRequiredError()
    const name = validateServiceAccountName(command.name)
    return this.repository.create(command.groupId, name)
  }
}
