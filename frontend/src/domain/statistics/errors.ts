/**
 * Statistics domain errors. The use case throws these; the presentation
 * layer catches them and maps to a user-facing toast. Every error
 * descends from StatisticsDomainError so a single catch block can funnel
 * them.
 */

export class StatisticsDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'StatisticsDomainError'
  }
}

export class StatisticsUnavailableError extends StatisticsDomainError {
  constructor(detail?: string) {
    super(detail ?? 'Failed to fetch statistics')
    this.name = 'StatisticsUnavailableError'
  }
}
