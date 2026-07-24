import type { StatisticsGateway } from '@/application/ports/StatisticsGateway'
import type { AdminStatistics } from '@/domain/statistics/Statistics'

/**
 * Test-only StatisticsGateway. Seed counts with `seed(...)` or make it
 * fail with `failWith(new Error(...))` to exercise the card's error path.
 * Mirrors the fake pattern used by InMemoryCsrfGateway.
 */
export class InMemoryStatisticsGateway implements StatisticsGateway {
  private next: AdminStatistics = {
    userCount: 0,
    groupCount: 0,
    passwordCount: 0,
    oneTimeLinkCount: 0,
    activeOneTimeLinkCount: 0,
  }
  private nextError: Error | null = null

  seed(statistics: AdminStatistics): this {
    this.next = statistics
    this.nextError = null
    return this
  }

  failWith(error: Error): this {
    this.nextError = error
    return this
  }

  async getAdminStatistics(): Promise<AdminStatistics> {
    if (this.nextError) throw this.nextError
    return this.next
  }
}
