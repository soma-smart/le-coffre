import type { ServiceAccountRepository } from '@/application/ports/ServiceAccountRepository'

export class GetServiceAccountApiUrlUseCase {
  constructor(private readonly repository: ServiceAccountRepository) {}

  execute(): string {
    return this.repository.apiUrl()
  }
}
