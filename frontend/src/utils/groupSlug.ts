import type { GroupItem } from '@/client/types.gen'

export const slugifyGroupName = (name: string): string => {
  return name
}

export const findGroupIdBySlug = (
  groupList: GroupItem[],
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
