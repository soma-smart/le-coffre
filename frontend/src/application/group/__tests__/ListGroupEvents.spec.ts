import { describe, expect, it } from 'vitest'
import { ListGroupEventsUseCase } from '@/application/group/ListGroupEvents'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'

function seedWithEvents() {
  const repo = new InMemoryGroupRepository().seed({
    id: 'g1',
    name: 'Team',
    isPersonal: false,
    userId: null,
    owners: ['u1'],
    members: ['u2'],
  })
  repo.addEvent('g1', {
    eventId: 'e1',
    eventType: 'UserAddedToGroupEvent',
    occurredOn: '2024-01-01T00:00:00Z',
    actorUserId: 'u1',
    actorEmail: 'owner@example.com',
    eventData: { groupId: 'g1', userId: 'u2', userEmail: 'u2@example.com' },
  })
  repo.addEvent('g1', {
    eventId: 'e2',
    eventType: 'OwnerAddedToGroupEvent',
    occurredOn: '2024-01-05T00:00:00Z',
    actorUserId: 'u1',
    actorEmail: 'owner@example.com',
    eventData: { groupId: 'g1', userId: 'u2', userEmail: 'u2@example.com' },
  })
  repo.addEvent('g1', {
    eventId: 'e3',
    eventType: 'UserRemovedFromGroupEvent',
    occurredOn: '2024-02-01T00:00:00Z',
    actorUserId: 'u1',
    actorEmail: 'owner@example.com',
    eventData: { groupId: 'g1', userId: 'u3', userEmail: 'u3@example.com' },
  })
  return repo
}

describe('ListGroupEventsUseCase', () => {
  it('returns every event when no filter is applied', async () => {
    const repo = seedWithEvents()
    const events = await new ListGroupEventsUseCase(repo).execute({ groupId: 'g1' })
    expect(events.map((e) => e.eventId)).toEqual(['e1', 'e2', 'e3'])
  })

  it('filters by event type', async () => {
    const repo = seedWithEvents()
    const events = await new ListGroupEventsUseCase(repo).execute({
      groupId: 'g1',
      eventTypes: ['OwnerAddedToGroupEvent'],
    })
    expect(events.map((e) => e.eventId)).toEqual(['e2'])
  })

  it('filters by date range (inclusive)', async () => {
    const repo = seedWithEvents()
    const events = await new ListGroupEventsUseCase(repo).execute({
      groupId: 'g1',
      startDate: '2024-01-02T00:00:00Z',
      endDate: '2024-01-31T00:00:00Z',
    })
    expect(events.map((e) => e.eventId)).toEqual(['e2'])
  })
})
