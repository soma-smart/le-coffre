import {
  createPasswordPasswordsPost,
  deletePasswordPasswordsPasswordIdDelete,
  getPasswordPasswordsPasswordIdGet,
  listPasswordAccessPasswordsPasswordIdAccessGet,
  listPasswordEventsPasswordsPasswordIdEventsGet,
  listPasswordsPasswordsListGet,
  sharePasswordPasswordsPasswordIdSharePost,
  unsharePasswordPasswordsPasswordIdShareGroupIdDelete,
  updatePasswordPasswordsPasswordIdPut,
} from '@/client/sdk.gen'
import type {
  GetPasswordListResponse,
  ListPasswordAccessResponse,
  PasswordEventResponse,
} from '@/client/types.gen'
import type {
  CreatePasswordInput,
  ListPasswordEventsFilters,
  PasswordRepository,
  UpdatePasswordInput,
} from '@/application/ports/PasswordRepository'
import type { Password, PasswordAccess, PasswordEvent } from '@/domain/password/Password'
import {
  PasswordAccessDeniedError,
  PasswordDomainError,
  PasswordNotFoundError,
} from '@/domain/password/errors'

/**
 * Backend adapter for PasswordRepository. Two jobs:
 *   1. Wrap every password-related SDK call.
 *   2. Translate between snake_case SDK DTOs and camelCase domain types,
 *      and between HTTP error codes and domain errors.
 *
 * The dependency rule (enforced by ESLint) is that only the Backend*
 * adapters and `@/customClient` may import `@/client/*`; presentation
 * code goes through use cases via useContainer().
 */
export class BackendPasswordRepository implements PasswordRepository {
  async list(): Promise<Password[]> {
    const response = await listPasswordsPasswordsListGet()
    this.throwIfError(response.error, response.response?.status)
    return (response.data ?? []).map(toPassword)
  }

  async getDecryptedValue(passwordId: string): Promise<string> {
    const response = await getPasswordPasswordsPasswordIdGet({
      path: { password_id: passwordId },
    })
    this.throwIfError(response.error, response.response?.status, passwordId)
    if (!response.data) throw new PasswordNotFoundError(passwordId)
    return response.data.password
  }

  async create(input: CreatePasswordInput): Promise<string> {
    const response = await createPasswordPasswordsPost({
      body: {
        name: input.name,
        password: input.password,
        folder: input.folder ?? null,
        login: input.login ?? null,
        url: input.url ?? null,
        group_id: input.groupId,
      },
    })
    this.throwIfError(response.error, response.response?.status)
    if (!response.data) throw new PasswordDomainError('Empty response from create password')
    return response.data.id
  }

  async update(input: UpdatePasswordInput): Promise<void> {
    const response = await updatePasswordPasswordsPasswordIdPut({
      path: { password_id: input.id },
      body: {
        name: input.name,
        password: input.password ?? null,
        folder: input.folder ?? null,
        login: input.login ?? null,
        url: input.url ?? null,
      },
    })
    this.throwIfError(response.error, response.response?.status, input.id)
  }

  async delete(passwordId: string): Promise<void> {
    const response = await deletePasswordPasswordsPasswordIdDelete({
      path: { password_id: passwordId },
    })
    this.throwIfError(response.error, response.response?.status, passwordId)
  }

  async share(passwordId: string, groupId: string): Promise<void> {
    const response = await sharePasswordPasswordsPasswordIdSharePost({
      path: { password_id: passwordId },
      body: { group_id: groupId },
    })
    this.throwIfError(response.error, response.response?.status, passwordId)
  }

  async unshare(passwordId: string, groupId: string): Promise<void> {
    const response = await unsharePasswordPasswordsPasswordIdShareGroupIdDelete({
      path: { password_id: passwordId, group_id: groupId },
    })
    this.throwIfError(response.error, response.response?.status, passwordId)
  }

  async listAccess(passwordId: string): Promise<PasswordAccess> {
    const response = await listPasswordAccessPasswordsPasswordIdAccessGet({
      path: { password_id: passwordId },
    })
    this.throwIfError(response.error, response.response?.status, passwordId)
    if (!response.data) throw new PasswordNotFoundError(passwordId)
    return toPasswordAccess(response.data)
  }

  async listEvents(
    passwordId: string,
    filters?: ListPasswordEventsFilters,
  ): Promise<PasswordEvent[]> {
    const response = await listPasswordEventsPasswordsPasswordIdEventsGet({
      path: { password_id: passwordId },
      query: {
        event_type: filters?.eventTypes?.length ? filters.eventTypes : undefined,
        start_date: filters?.startDate,
        end_date: filters?.endDate,
      },
    })
    this.throwIfError(response.error, response.response?.status, passwordId)
    return (response.data?.events ?? []).map(toPasswordEvent)
  }

  private throwIfError(error: unknown, status: number | undefined, passwordId?: string): void {
    if (!error) return
    if (status === 404 && passwordId) throw new PasswordNotFoundError(passwordId)
    if (status === 403 && passwordId) throw new PasswordAccessDeniedError(passwordId)
    throw new PasswordDomainError(extractDetail(error) ?? 'Password operation failed')
  }
}

function toPassword(dto: GetPasswordListResponse): Password {
  return {
    id: dto.id,
    name: dto.name,
    folder: dto.folder,
    groupId: dto.group_id,
    createdAt: dto.created_at,
    lastUpdatedAt: dto.last_updated_at,
    canRead: dto.can_read,
    canWrite: dto.can_write,
    login: dto.login,
    url: dto.url,
    accessibleGroupIds: dto.accessible_group_ids,
  }
}

function toPasswordAccess(dto: ListPasswordAccessResponse): PasswordAccess {
  return {
    resourceId: dto.resource_id,
    users: dto.user_access_list.map((item) => ({
      userId: item.user_id,
      permissions: item.permissions,
      isOwner: item.is_owner,
    })),
    groups: dto.group_access_list.map((item) => ({
      userId: item.user_id,
      permissions: item.permissions,
      isOwner: item.is_owner,
    })),
  }
}

function toPasswordEvent(dto: PasswordEventResponse): PasswordEvent {
  return {
    eventId: dto.event_id,
    eventType: dto.event_type,
    occurredOn: dto.occurred_on,
    actorUserId: dto.actor_user_id,
    actorEmail: dto.actor_email,
    eventData: toPasswordEventData(dto.event_data),
  }
}

/**
 * Map every snake_case key inside the event payload to camelCase before it
 * crosses the infrastructure boundary. Keeping this in the adapter lets the
 * presentation layer talk only camelCase — the backend's wire format never
 * leaks past this file.
 *
 * Unknown keys are still forwarded (camelCased) so a new event-data field
 * shipped on the server appears in the UI without code change; rendering
 * still requires a code change, but it won't crash.
 *
 * Exported for unit testing only — production code should never import it.
 */
export function toPasswordEventData(raw: unknown): Record<string, unknown> {
  if (!raw || typeof raw !== 'object') return {}
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    out[snakeToCamel(key)] = value
  }
  return out
}

function snakeToCamel(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_, ch) => ch.toUpperCase())
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
