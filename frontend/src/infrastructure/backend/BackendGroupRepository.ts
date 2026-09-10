import {
  addMemberToGroupGroupsGroupIdMembersPost,
  addOwnerToGroupGroupsGroupIdOwnersPost,
  createGroupGroupsPost,
  deleteGroupGroupsGroupIdDelete,
  getGroupGroupsGroupIdGet,
  listGroupEventsGroupsGroupIdEventsGet,
  listGroupsGroupsGet,
  removeMemberFromGroupGroupsGroupIdMembersUserIdDelete,
  updateGroupGroupsGroupIdPut,
} from '@/client/sdk.gen'
import type { GetGroupResponse, GroupEventResponse, GroupItem } from '@/client/types.gen'
import type {
  GroupRepository,
  ListGroupEventsFilters,
  ListGroupsFilters,
} from '@/application/ports/GroupRepository'
import type { Group, GroupEvent } from '@/domain/group/Group'
import { GroupAccessDeniedError, GroupDomainError, GroupNotFoundError } from '@/domain/group/errors'

/**
 * Backend adapter for GroupRepository. Wraps every /groups/* SDK
 * function and maps snake_case DTOs → camelCase domain Group. 404
 * becomes GroupNotFoundError; anything else bubbles up as a
 * GroupDomainError carrying the backend detail string.
 */
export class BackendGroupRepository implements GroupRepository {
  async list(filters?: ListGroupsFilters): Promise<Group[]> {
    const includePersonal = filters?.includePersonal ?? true
    const response = await listGroupsGroupsGet({ query: { include_personal: includePersonal } })
    this.throwIfError(response.error, response.response?.status)
    return (response.data?.groups ?? []).map(toGroup)
  }

  async get(groupId: string): Promise<Group> {
    const response = await getGroupGroupsGroupIdGet({ path: { group_id: groupId } })
    this.throwIfError(response.error, response.response?.status, groupId)
    if (!response.data) throw new GroupNotFoundError(groupId)
    return toGroup(response.data)
  }

  async create(name: string): Promise<string> {
    const response = await createGroupGroupsPost({ body: { name } })
    this.throwIfError(response.error, response.response?.status)
    if (!response.data) throw new GroupDomainError('Empty response from create group')
    return response.data.id
  }

  async update(groupId: string, name: string): Promise<void> {
    const response = await updateGroupGroupsGroupIdPut({
      path: { group_id: groupId },
      body: { name },
    })
    this.throwIfError(response.error, response.response?.status, groupId)
  }

  async delete(groupId: string): Promise<void> {
    const response = await deleteGroupGroupsGroupIdDelete({ path: { group_id: groupId } })
    this.throwIfError(response.error, response.response?.status, groupId)
  }

  async addMember(groupId: string, userId: string): Promise<void> {
    const response = await addMemberToGroupGroupsGroupIdMembersPost({
      path: { group_id: groupId },
      body: { user_id: userId },
    })
    this.throwIfError(response.error, response.response?.status, groupId)
  }

  async removeMember(groupId: string, userId: string): Promise<void> {
    const response = await removeMemberFromGroupGroupsGroupIdMembersUserIdDelete({
      path: { group_id: groupId, user_id: userId },
    })
    this.throwIfError(response.error, response.response?.status, groupId)
  }

  async promoteToOwner(groupId: string, userId: string): Promise<void> {
    const response = await addOwnerToGroupGroupsGroupIdOwnersPost({
      path: { group_id: groupId },
      body: { user_id: userId },
    })
    this.throwIfError(response.error, response.response?.status, groupId)
  }

  async listEvents(groupId: string, filters?: ListGroupEventsFilters): Promise<GroupEvent[]> {
    const response = await listGroupEventsGroupsGroupIdEventsGet({
      path: { group_id: groupId },
      query: {
        event_type: filters?.eventTypes?.length ? filters.eventTypes : undefined,
        start_date: filters?.startDate,
        end_date: filters?.endDate,
      },
    })
    this.throwIfError(response.error, response.response?.status, groupId)
    return (response.data?.events ?? []).map(toGroupEvent)
  }

  private throwIfError(error: unknown, status: number | undefined, groupId?: string): void {
    if (!error) return
    if (status === 404 && groupId) throw new GroupNotFoundError(groupId)
    if (status === 403 && groupId) throw new GroupAccessDeniedError(groupId)
    throw new GroupDomainError(extractDetail(error) ?? 'Group operation failed')
  }
}

function toGroup(dto: GroupItem | GetGroupResponse): Group {
  return {
    id: dto.id,
    name: dto.name,
    isPersonal: dto.is_personal,
    userId: dto.user_id,
    owners: dto.owners,
    members: dto.members,
  }
}

function toGroupEvent(dto: GroupEventResponse): GroupEvent {
  return {
    eventId: dto.event_id,
    eventType: dto.event_type,
    occurredOn: dto.occurred_on,
    actorUserId: dto.actor_user_id,
    actorEmail: dto.actor_email,
    eventData: toGroupEventData(dto.event_data),
  }
}

/**
 * Map every snake_case key inside the event payload to camelCase before it
 * crosses the infrastructure boundary, mirroring toPasswordEventData in
 * BackendPasswordRepository. Keeps the presentation layer talking only
 * camelCase.
 *
 * Exported for unit testing only — production code should never import it.
 */
export function toGroupEventData(raw: unknown): Record<string, unknown> {
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
