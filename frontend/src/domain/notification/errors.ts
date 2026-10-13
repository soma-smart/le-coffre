/**
 * Notification domain errors. Every error descends from
 * NotificationDomainError so a single catch block can funnel them.
 */

export class NotificationDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'NotificationDomainError'
  }
}
