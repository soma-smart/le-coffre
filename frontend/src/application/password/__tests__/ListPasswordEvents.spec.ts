import { describe, expect, it } from 'vitest'
import { ListPasswordEventsUseCase } from '@/application/password/ListPasswordEvents'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'

function seedWithEvents() {
  const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
  return repo.create({ name: 'Gmail', password: 'x', groupId: 'g' }).then(() => {
    repo.addEvent('pwd-1', {
      eventId: 'e1',
      eventType: 'PasswordCreatedEvent',
      occurredOn: '2024-01-01T00:00:00Z',
      actorUserId: 'u',
      actorEmail: 'u@example.com',
      eventData: { folder: 'default' },
    })
    repo.addEvent('pwd-1', {
      eventId: 'e2',
      eventType: 'PasswordSharedEvent',
      occurredOn: '2024-01-05T00:00:00Z',
      actorUserId: 'u',
      actorEmail: 'u@example.com',
      eventData: { sharedWithGroupId: 'g2' },
    })
    repo.addEvent('pwd-1', {
      eventId: 'e3',
      eventType: 'PasswordUpdatedEvent',
      occurredOn: '2024-02-01T00:00:00Z',
      actorUserId: 'u',
      actorEmail: 'u@example.com',
      eventData: { hasNameChanged: true },
    })
    return repo
  })
}

describe('ListPasswordEventsUseCase', () => {
  it('returns every event when no filter is applied', async () => {
    const repo = await seedWithEvents()
    const events = await new ListPasswordEventsUseCase(repo).execute({ passwordId: 'pwd-1' })
    expect(events.map((e) => e.eventId)).toEqual(['e1', 'e2', 'e3'])
  })

  it('filters by event type', async () => {
    const repo = await seedWithEvents()
    const events = await new ListPasswordEventsUseCase(repo).execute({
      passwordId: 'pwd-1',
      eventTypes: ['PasswordSharedEvent'],
    })
    expect(events.map((e) => e.eventId)).toEqual(['e2'])
  })

  it('filters by date range (inclusive)', async () => {
    const repo = await seedWithEvents()
    const events = await new ListPasswordEventsUseCase(repo).execute({
      passwordId: 'pwd-1',
      startDate: '2024-01-02T00:00:00Z',
      endDate: '2024-01-31T00:00:00Z',
    })
    expect(events.map((e) => e.eventId)).toEqual(['e2'])
  })
})
