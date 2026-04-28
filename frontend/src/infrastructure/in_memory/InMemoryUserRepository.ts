import type {
  CreateUserInput,
  UpdateUserInput,
  UpdateUserPasswordInput,
  UserRepository,
} from '@/application/ports/UserRepository'
import { ADMIN_ROLE, type User } from '@/domain/user/User'
import { IncorrectOldPasswordError, UserNotFoundError } from '@/domain/user/errors'

/**
 * Test-only implementation of UserRepository. Mirrors the fake pattern
 * used by InMemoryPasswordRepository: useIdGenerator / seed /
 * setCurrent / setPassword helpers let a spec lay down deterministic
 * state without going through the write APIs.
 */
export class InMemoryUserRepository implements UserRepository {
  private readonly storage = new Map<string, User>()
  private readonly passwords = new Map<string, string>()
  private current: User | null = null
  private idGenerator: () => string = randomUuid

  useIdGenerator(generator: () => string): this {
    this.idGenerator = generator
    return this
  }

  seed(user: User, password = 'seeded-password'): this {
    this.storage.set(user.id, user)
    this.passwords.set(user.id, password)
    return this
  }

  setCurrent(user: User | null): this {
    this.current = user
    if (user) this.storage.set(user.id, user)
    return this
  }

  setPassword(userId: string, password: string): this {
    this.passwords.set(userId, password)
    return this
  }

  async getCurrent(): Promise<User | null> {
    return this.current
  }

  async get(userId: string): Promise<User> {
    const user = this.storage.get(userId)
    if (!user) throw new UserNotFoundError(userId)
    return user
  }

  async list(): Promise<User[]> {
    return Array.from(this.storage.values())
  }

  async create(input: CreateUserInput): Promise<string> {
    const id = this.idGenerator()
    const user: User = {
      id,
      username: input.username,
      email: input.email,
      name: input.name,
      roles: [],
      personalGroupId: null,
      isSso: false,
    }
    this.storage.set(id, user)
    this.passwords.set(id, input.password)
    return id
  }

  async update(input: UpdateUserInput): Promise<void> {
    const user = this.storage.get(input.id)
    if (!user) throw new UserNotFoundError(input.id)
    this.storage.set(input.id, {
      ...user,
      username: input.username,
      email: input.email,
      name: input.name,
    })
  }

  async updatePassword(input: UpdateUserPasswordInput): Promise<void> {
    if (!this.current) throw new UserNotFoundError('(no current user)')
    const stored = this.passwords.get(this.current.id)
    if (stored !== input.oldPassword) {
      throw new IncorrectOldPasswordError()
    }
    this.passwords.set(this.current.id, input.newPassword)
  }

  async delete(userId: string): Promise<void> {
    if (!this.storage.has(userId)) throw new UserNotFoundError(userId)
    this.storage.delete(userId)
    this.passwords.delete(userId)
  }

  async promoteToAdmin(userId: string): Promise<void> {
    const user = this.storage.get(userId)
    if (!user) throw new UserNotFoundError(userId)
    if (!user.roles.includes(ADMIN_ROLE)) {
      this.storage.set(userId, { ...user, roles: [...user.roles, ADMIN_ROLE] })
    }
  }
}

function randomUuid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `test-${Math.random().toString(36).slice(2)}`
}
