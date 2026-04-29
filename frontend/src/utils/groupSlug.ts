import type { Group } from '@/domain/group/Group'

export const slugifyGroupName = (name: string): string => {
  return name
}

export const findGroupIdBySlug = (
  groupList: Group[],
  slug: string | null | undefined,
): string | null => {
  if (!slug) return null

  const decodedSlug = (() => {
    try {
      return decodeURIComponent(slug)
    } catch {
      return slug
    }
  })()

  const match = groupList.find(
    (group) => group.name === decodedSlug || encodeURIComponent(group.name) === slug,
  )
  return match?.id ?? null
}
