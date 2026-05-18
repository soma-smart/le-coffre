import type { Group } from '@/domain/group/Group'

export interface ListGroupsFilters {
  includePersonal?: boolean
}

export interface GroupRepository {
  list(filters?: ListGroupsFilters): Promise<Group[]>
  get(groupId: string): Promise<Group>
  create(name: string): Promise<string>
  update(groupId: string, name: string): Promise<void>
  delete(groupId: string): Promise<void>
  addMember(groupId: string, userId: string): Promise<void>
  removeMember(groupId: string, userId: string): Promise<void>
  promoteToOwner(groupId: string, userId: string): Promise<void>
}
