import type { AdminStatistics } from '@/domain/statistics/Statistics'

/**
 * Contract the infrastructure must satisfy to feed the admin statistics
 * dashboard. One method expressing the business intent — "give me the
 * admin-wide counts" — regardless of how many backend calls it takes.
 */
export interface StatisticsGateway {
  getAdminStatistics(): Promise<AdminStatistics>
}
