import type { Group, GroupEvent } from '@/domain/group/Group'

export interface ListGroupsFilters {
  includePersonal?: boolean
}

export interface ListGroupEventsFilters {
  eventTypes?: string[]
  startDate?: string
  endDate?: string
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
  listEvents(groupId: string, filters?: ListGroupEventsFilters): Promise<GroupEvent[]>
}
