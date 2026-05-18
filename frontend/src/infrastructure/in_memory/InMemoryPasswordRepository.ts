import type {
  CreatePasswordInput,
  ListPasswordEventsFilters,
  PasswordRepository,
  UpdatePasswordInput,
} from '@/application/ports/PasswordRepository'
import type { Password, PasswordAccess, PasswordEvent } from '@/domain/password/Password'
import { PasswordNotFoundError } from '@/domain/password/errors'

/**
 * Test-only implementation of PasswordRepository.
 *
 * Used by every unit + component test (no network). Mirrors the
 * tests/fakes/ pattern from the backend: useIdGenerator + seed helpers
 * let a test set up deterministic state without going through the
 * write APIs.
 */

interface StoredPassword {
  entity: Password
  decrypted: string
  sharedWithGroups: Set<string>
}

export class InMemoryPasswordRepository implements PasswordRepository {
  private readonly storage = new Map<string, StoredPassword>()
  private readonly events = new Map<string, PasswordEvent[]>()
  private idGenerator: () => string = randomUuid

  useIdGenerator(generator: () => string): this {
    this.idGenerator = generator
    return this
  }

  seed(password: Password, decrypted = 'seeded-secret'): this {
    this.storage.set(password.id, {
      entity: password,
      decrypted,
      sharedWithGroups: new Set([password.groupId, ...password.accessibleGroupIds]),
    })
    return this
  }

  addEvent(passwordId: string, event: PasswordEvent): this {
    const bucket = this.events.get(passwordId) ?? []
    bucket.push(event)
    this.events.set(passwordId, bucket)
    return this
  }

  async list(): Promise<Password[]> {
    return Array.from(this.storage.values(), (entry) => entry.entity)
  }

  async getDecryptedValue(passwordId: string): Promise<string> {
    const entry = this.storage.get(passwordId)
    if (!entry) throw new PasswordNotFoundError(passwordId)
    return entry.decrypted
  }

  async create(input: CreatePasswordInput): Promise<string> {
    const id = this.idGenerator()
    const now = new Date().toISOString()
    const entity: Password = {
      id,
      name: input.name,
      folder: input.folder ?? '',
      groupId: input.groupId,
      createdAt: now,
      lastUpdatedAt: now,
      canRead: true,
      canWrite: true,
      login: input.login ?? null,
      url: input.url ?? null,
      accessibleGroupIds: [input.groupId],
    }
    this.storage.set(id, {
      entity,
      decrypted: input.password,
      sharedWithGroups: new Set([input.groupId]),
    })
    return id
  }

  async update(input: UpdatePasswordInput): Promise<void> {
    const entry = this.storage.get(input.id)
    if (!entry) throw new PasswordNotFoundError(input.id)
    entry.entity = {
      ...entry.entity,
      name: input.name,
      folder: input.folder ?? entry.entity.folder,
      login: input.login ?? entry.entity.login,
      url: input.url ?? entry.entity.url,
      lastUpdatedAt: new Date().toISOString(),
    }
    if (input.password) entry.decrypted = input.password
  }

  async delete(passwordId: string): Promise<void> {
    if (!this.storage.has(passwordId)) throw new PasswordNotFoundError(passwordId)
    this.storage.delete(passwordId)
    this.events.delete(passwordId)
  }

  async share(passwordId: string, groupId: string): Promise<void> {
    const entry = this.storage.get(passwordId)
    if (!entry) throw new PasswordNotFoundError(passwordId)
    entry.sharedWithGroups.add(groupId)
    entry.entity = {
      ...entry.entity,
      accessibleGroupIds: Array.from(entry.sharedWithGroups),
    }
  }

  async unshare(passwordId: string, groupId: string): Promise<void> {
    const entry = this.storage.get(passwordId)
    if (!entry) throw new PasswordNotFoundError(passwordId)
    entry.sharedWithGroups.delete(groupId)
    entry.entity = {
      ...entry.entity,
      accessibleGroupIds: Array.from(entry.sharedWithGroups),
    }
  }

  async listAccess(passwordId: string): Promise<PasswordAccess> {
    const entry = this.storage.get(passwordId)
    if (!entry) throw new PasswordNotFoundError(passwordId)
    return {
      resourceId: passwordId,
      users: [],
      groups: Array.from(entry.sharedWithGroups, (groupId) => ({
        userId: groupId,
        permissions: ['read'] as Array<'read'>,
        isOwner: groupId === entry.entity.groupId,
      })),
    }
  }

  async listEvents(
    passwordId: string,
    filters?: ListPasswordEventsFilters,
  ): Promise<PasswordEvent[]> {
    if (!this.storage.has(passwordId)) throw new PasswordNotFoundError(passwordId)
    let events = [...(this.events.get(passwordId) ?? [])]
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
