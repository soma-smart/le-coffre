import type { Password, PasswordAccess, PasswordEvent } from '@/domain/password/Password'

/**
 * Everything the password use cases need from the outside world.
 *
 * Two implementations satisfy this port:
 *   - infrastructure/backend/BackendPasswordRepository — wraps @/client
 *     for production (translates SDK DTOs ↔ domain types).
 *   - infrastructure/in_memory/InMemoryPasswordRepository — test-only
 *     fake used by every unit + component test.
 */

export interface CreatePasswordInput {
  name: string
  password: string
  groupId: string
  folder?: string | null
  login?: string | null
  url?: string | null
}

export interface UpdatePasswordInput {
  id: string
  name: string
  password?: string | null
  folder?: string | null
  login?: string | null
  url?: string | null
}

export interface ListPasswordEventsFilters {
  eventTypes?: string[]
  startDate?: string
  endDate?: string
}

export interface PasswordRepository {
  list(): Promise<Password[]>
  getDecryptedValue(passwordId: string): Promise<string>
  create(input: CreatePasswordInput): Promise<string>
  update(input: UpdatePasswordInput): Promise<void>
  delete(passwordId: string): Promise<void>
  share(passwordId: string, groupId: string): Promise<void>
  unshare(passwordId: string, groupId: string): Promise<void>
  listAccess(passwordId: string): Promise<PasswordAccess>
  listEvents(passwordId: string, filters?: ListPasswordEventsFilters): Promise<PasswordEvent[]>
}
