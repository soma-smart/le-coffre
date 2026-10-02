import type { ServiceAccountRepository } from '@/application/ports/ServiceAccountRepository'
import type { ServiceAccountPage } from '@/domain/serviceAccount/ServiceAccount'
import { ServiceAccountGroupRequiredError } from '@/domain/serviceAccount/errors'

export class ListServiceAccountsUseCase {
  constructor(private readonly repository: ServiceAccountRepository) {}

  async execute(groupId: string): Promise<ServiceAccountPage> {
    if (!groupId) throw new ServiceAccountGroupRequiredError()
    return this.repository.listForGroup(groupId)
  }
}
