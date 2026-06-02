import type { StatisticsGateway } from '@/application/ports/StatisticsGateway'
import type { AdminStatistics } from '@/domain/statistics/Statistics'

/**
 * Fetches the admin dashboard counts. Errors propagate — the presentation
 * layer (StatisticsCard) catches them and maps to a user-visible toast.
 */
export class GetAdminStatisticsUseCase {
  constructor(private readonly gateway: StatisticsGateway) {}

  execute(): Promise<AdminStatistics> {
    return this.gateway.getAdminStatistics()
  }
}
