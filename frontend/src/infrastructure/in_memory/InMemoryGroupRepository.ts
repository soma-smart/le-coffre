import type {
  GroupRepository,
  ListGroupEventsFilters,
  ListGroupsFilters,
} from '@/application/ports/GroupRepository'
import type { Group, GroupEvent } from '@/domain/group/Group'
import { GroupNotFoundError } from '@/domain/group/errors'

/**
 * Test-only implementation of GroupRepository. seed() pre-populates
 * state without going through the write APIs; useIdGenerator makes
 * `create` deterministic.
 */
export class InMemoryGroupRepository implements GroupRepository {
  private readonly storage = new Map<string, Group>()
  private readonly events = new Map<string, GroupEvent[]>()
  private idGenerator: () => string = randomUuid

  useIdGenerator(generator: () => string): this {
    this.idGenerator = generator
    return this
  }

  seed(group: Group): this {
    this.storage.set(group.id, group)
    return this
  }

  addEvent(groupId: string, event: GroupEvent): this {
    const bucket = this.events.get(groupId) ?? []
    bucket.push(event)
    this.events.set(groupId, bucket)
    return this
  }

  async list(filters?: ListGroupsFilters): Promise<Group[]> {
    const all = Array.from(this.storage.values())
    if (filters?.includePersonal === false) {
      return all.filter((g) => !g.isPersonal)
    }
    return all
  }

  async get(groupId: string): Promise<Group> {
    const group = this.storage.get(groupId)
    if (!group) throw new GroupNotFoundError(groupId)
    return group
  }

  async create(name: string): Promise<string> {
    const id = this.idGenerator()
    this.storage.set(id, {
      id,
      name,
      isPersonal: false,
      userId: null,
      owners: [],
      members: [],
    })
    return id
  }

  async update(groupId: string, name: string): Promise<void> {
    const group = this.storage.get(groupId)
    if (!group) throw new GroupNotFoundError(groupId)
    this.storage.set(groupId, { ...group, name })
  }

  async delete(groupId: string): Promise<void> {
    if (!this.storage.has(groupId)) throw new GroupNotFoundError(groupId)
    this.storage.delete(groupId)
  }

  async addMember(groupId: string, userId: string): Promise<void> {
    const group = this.storage.get(groupId)
    if (!group) throw new GroupNotFoundError(groupId)
    if (!group.members.includes(userId)) {
      this.storage.set(groupId, { ...group, members: [...group.members, userId] })
    }
  }

  async removeMember(groupId: string, userId: string): Promise<void> {
    const group = this.storage.get(groupId)
    if (!group) throw new GroupNotFoundError(groupId)
    this.storage.set(groupId, {
      ...group,
      members: group.members.filter((id) => id !== userId),
      owners: group.owners.filter((id) => id !== userId),
    })
  }

  async promoteToOwner(groupId: string, userId: string): Promise<void> {
    const group = this.storage.get(groupId)
    if (!group) throw new GroupNotFoundError(groupId)
    if (!group.owners.includes(userId)) {
      this.storage.set(groupId, { ...group, owners: [...group.owners, userId] })
    }
  }

  async listEvents(groupId: string, filters?: ListGroupEventsFilters): Promise<GroupEvent[]> {
    if (!this.storage.has(groupId)) throw new GroupNotFoundError(groupId)
    let events = [...(this.events.get(groupId) ?? [])]
    if (filters?.eventTypes?.length) {
      const set = new Set(filters.eventTypes)
      events = events.filter((event) => set.has(event.eventType))
    }
    if (filters?.startDate) {
      const min = new Date(filters.startDate).getTime()
      events = events.filter((event) => new Date(event.occurredOn).getTime() >= min)
    }
    if (filters?.endDate) {
      const max = new Date(filters.endDate).getTime()
      events = events.filter((event) => new Date(event.occurredOn).getTime() <= max)
    }
    return events
  }
}

function randomUuid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `test-${Math.random().toString(36).slice(2)}`
}
