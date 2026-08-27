/**
 * A vault entry as the popup sees it. Metadata only: the secret is never part
 * of this type and never reaches the popup at all.
 *
 * Ported from frontend/src/domain/password/Password.ts. Copied rather than
 * imported: a cross-package import breaks this package's rootDir and drags Vue
 * types into the extension build.
 */
export interface Entry {
  id: string
  name: string
  folder: string
  login: string | null
  url: string | null
  groupId: string
  accessibleGroupIds: string[]
  canRead: boolean
  canWrite: boolean
  accessExpiresAt: string | null
}

/**
 * Every group that can reach this entry.
 *
 * Ported from `accessibleGroupIdsFor`. The empty-array case is the whole point:
 * an unshared entry has no `accessible_group_ids`, and its owning group is then
 * the only reader. Filtering on `groupId` alone would make every *shared* entry
 * vanish from the extension while it stays visible in the web app.
 */
export function accessibleGroupIdsFor(entry: Entry): string[] {
  return entry.accessibleGroupIds.length > 0 ? entry.accessibleGroupIds : [entry.groupId]
}

/** Ported from `matchesPasswordQuery`, minus the group name the popup lacks. */
export function matchesEntryQuery(entry: Entry, query: string): boolean {
  const needle = query.trim().toLowerCase()
  if (!needle) return true

  return (
    entry.folder.toLowerCase().includes(needle) ||
    entry.name.toLowerCase().includes(needle) ||
    (entry.login?.toLowerCase().includes(needle) ?? false) ||
    (entry.url?.toLowerCase().includes(needle) ?? false)
  )
}

/** An entry whose time-limited share has lapsed. The server would 404 it. */
export function isShareExpired(entry: Entry, now: Date): boolean {
  if (!entry.accessExpiresAt) return false
  return new Date(entry.accessExpiresAt).getTime() <= now.getTime()
}

export interface VisibleEntries {
  entries: Entry[]
  /** How many were dropped, so the list can say so rather than look wrong. */
  hiddenCount: number
}

/**
 * What the popup should show for one group.
 *
 * Drops entries the caller cannot actually read and shares that have lapsed. A
 * copy-only client can do nothing with either, and silently showing them would
 * produce buttons that always fail.
 */
export function visibleEntriesForGroup(
  entries: readonly Entry[],
  groupId: string,
  now: Date,
): VisibleEntries {
  const inGroup = entries.filter((entry) => accessibleGroupIdsFor(entry).includes(groupId))
  const visible = inGroup.filter((entry) => entry.canRead && !isShareExpired(entry, now))

  return {
    entries: [...visible].sort((left, right) => left.name.localeCompare(right.name)),
    hiddenCount: inGroup.length - visible.length,
  }
}
