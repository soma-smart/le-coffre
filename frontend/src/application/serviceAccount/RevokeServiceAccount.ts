import type { ServiceAccountRepository } from '@/application/ports/ServiceAccountRepository'

export class RevokeServiceAccountUseCase {
  constructor(private readonly repository: ServiceAccountRepository) {}

  async execute(serviceAccountId: string): Promise<void> {
    return this.repository.revoke(serviceAccountId)
  }
}
