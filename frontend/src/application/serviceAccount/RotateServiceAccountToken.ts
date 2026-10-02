import type { ServiceAccountRepository } from '@/application/ports/ServiceAccountRepository'
import type { RotatedServiceAccountToken } from '@/domain/serviceAccount/ServiceAccount'

export class RotateServiceAccountTokenUseCase {
  constructor(private readonly repository: ServiceAccountRepository) {}

  async execute(serviceAccountId: string): Promise<RotatedServiceAccountToken> {
    return this.repository.rotate(serviceAccountId)
  }
}
