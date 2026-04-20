import {
  createUserUsersPost,
  deleteUserUsersUserIdDelete,
  getUserMeUsersMeGet,
  getUserUsersUserIdGet,
  listUsersUsersGet,
  promoteUserToAdminUsersUserIdPromoteAdminPost,
  updateUserPasswordUsersMePasswordPut,
  updateUserUsersUserIdPut,
} from '@/client/sdk.gen'
import type { GetUserMeResponse, GetUserResponse, ListUserResponse } from '@/client/types.gen'
import type {
  CreateUserInput,
  UpdateUserInput,
  UpdateUserPasswordInput,
  UserRepository,
} from '@/application/ports/UserRepository'
import type { User } from '@/domain/user/User'
import { UserDomainError, UserNotFoundError } from '@/domain/user/errors'

/**
 * Backend adapter for UserRepository. The only file outside the other
 * sanctioned @/client importers allowed to touch user SDK calls; maps
 * snake_case DTOs into the camelCase domain User, and HTTP errors into
 * domain errors.
 */
export class BackendUserRepository implements UserRepository {
  async getCurrent(): Promise<User | null> {
    const response = await getUserMeUsersMeGet()
    if (response.response?.status === 401) return null
    this.throwIfError(response.error, response.response?.status)
    return response.data ? meToUser(response.data) : null
  }

  async get(userId: string): Promise<User> {
    const response = await getUserUsersUserIdGet({ path: { user_id: userId } })
    this.throwIfError(response.error, response.response?.status, userId)
    if (!response.data) throw new UserNotFoundError(userId)
    return basicToUser(response.data)
  }

  async list(): Promise<User[]> {
    const response = await listUsersUsersGet()
    this.throwIfError(response.error, response.response?.status)
    return (response.data ?? []).map(listItemToUser)
  }

  async create(input: CreateUserInput): Promise<string> {
    const response = await createUserUsersPost({
      body: {
        username: input.username,
        email: input.email,
        name: input.name,
        password: input.password,
      },
    })
    this.throwIfError(response.error, response.response?.status)
    if (!response.data) throw new UserDomainError('Empty response from create user')
    return response.data.id
  }

  async update(input: UpdateUserInput): Promise<void> {
    const response = await updateUserUsersUserIdPut({
      path: { user_id: input.id },
      body: {
        username: input.username,
        email: input.email,
        name: input.name,
      },
    })
    this.throwIfError(response.error, response.response?.status, input.id)
  }

  async updatePassword(input: UpdateUserPasswordInput): Promise<void> {
    const response = await updateUserPasswordUsersMePasswordPut({
      body: { old_password: input.oldPassword, new_password: input.newPassword },
    })
    this.throwIfError(response.error, response.response?.status)
  }

  async delete(userId: string): Promise<void> {
    const response = await deleteUserUsersUserIdDelete({ path: { user_id: userId } })
    this.throwIfError(response.error, response.response?.status, userId)
  }

  async promoteToAdmin(userId: string): Promise<void> {
    const response = await promoteUserToAdminUsersUserIdPromoteAdminPost({
      path: { user_id: userId },
    })
    this.throwIfError(response.error, response.response?.status, userId)
  }

  private throwIfError(error: unknown, status: number | undefined, userId?: string): void {
    if (!error) return
    if (status === 404 && userId) throw new UserNotFoundError(userId)
    throw new UserDomainError(extractDetail(error) ?? 'User operation failed')
  }
}

function meToUser(dto: GetUserMeResponse): User {
  return {
    id: dto.id,
    username: dto.username,
    email: dto.email,
    name: dto.name,
    roles: dto.roles,
    personalGroupId: dto.personal_group_id ?? null,
    isSso: dto.is_sso,
  }
}

function basicToUser(dto: GetUserResponse): User {
  return {
    id: dto.id,
    username: dto.username,
    email: dto.email,
    name: dto.name,
    roles: dto.roles ?? [],
    personalGroupId: null,
    isSso: false,
  }
}

function listItemToUser(dto: ListUserResponse): User {
  return {
    id: dto.id,
    username: dto.username,
    email: dto.email,
    name: dto.name,
    roles: dto.roles,
    personalGroupId: null,
    isSso: false,
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
