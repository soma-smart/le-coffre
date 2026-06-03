import type { User } from '@/domain/user/User'

export interface CreateUserInput {
  username: string
  email: string
  name: string
  password: string
}

export interface UpdateUserInput {
  id: string
  username: string
  email: string
  name: string
}

export interface UpdateUserPasswordInput {
  oldPassword: string
  newPassword: string
}

/**
 * Everything the user use cases need from the outside world. The
 * production implementation wraps @/client; tests use
 * InMemoryUserRepository.
 */
export interface UserRepository {
  /** null when no authenticated user is available (e.g. 401 after logout). */
  getCurrent(): Promise<User | null>
  get(userId: string): Promise<User>
  list(): Promise<User[]>
  create(input: CreateUserInput): Promise<string>
  update(input: UpdateUserInput): Promise<void>
  updatePassword(input: UpdateUserPasswordInput): Promise<void>
  delete(userId: string): Promise<void>
  promoteToAdmin(userId: string): Promise<void>
}
