import {
  addMemberToGroupGroupsGroupIdMembersPost,
  addOwnerToGroupGroupsGroupIdOwnersPost,
  createGroupGroupsPost,
  deleteGroupGroupsGroupIdDelete,
  getGroupGroupsGroupIdGet,
  listGroupsGroupsGet,
  removeMemberFromGroupGroupsGroupIdMembersUserIdDelete,
  updateGroupGroupsGroupIdPut,
} from '@/client/sdk.gen'
import type { GetGroupResponse, GroupItem } from '@/client/types.gen'
import type { GroupRepository, ListGroupsFilters } from '@/application/ports/GroupRepository'
import type { Group } from '@/domain/group/Group'
import { GroupDomainError, GroupNotFoundError } from '@/domain/group/errors'

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

  private throwIfError(error: unknown, status: number | undefined, groupId?: string): void {
    if (!error) return
    if (status === 404 && groupId) throw new GroupNotFoundError(groupId)
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

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
