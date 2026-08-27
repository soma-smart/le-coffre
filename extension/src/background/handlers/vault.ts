/**
 * Reading the vault: groups, entries, and the one call that reveals a secret.
 */
import { visibleEntriesForGroup, matchesEntryQuery, type Entry } from '@/domain/entry'
import { err, ok, type Result } from '@/domain/errors'
import { filterGroupsForUser, isUserOwnerOf, sortGroups } from '@/domain/group'
import { matchesDomain, MATCH_RANK } from '@/domain/matchesDomain'
import type { ConnectionState, EntrySummary, GroupSummary } from '@/shared/messages'
import { LOCAL_KEYS, SESSION_KEYS } from '@/shared/storageKeys'

import type { Deps } from '../deps'
import { clearCredentials, readToken, readVaultUrl, stampActivity } from '../session'
import { getConnectionState } from './connection'

const ENTRIES_CACHE_TTL_MS = 60_000

interface CachedEntries {
  entries: Entry[]
  fetchedAt: string
}

/** Resolve an authenticated client, or say why not. */
async function authenticated(deps: Deps) {
  const vaultUrl = await readVaultUrl(deps.browser)
  if (!vaultUrl) return err({ kind: 'NOT_CONFIGURED' as const })

  const token = await readToken(deps.browser, deps.clock.now())
  if (!token) return err({ kind: 'AUTH_LOST' as const, reason: 'expired' as const })

  return ok({ vaultUrl, client: deps.makeClient(vaultUrl, token) })
}

/** A 401 means the credential is gone for good; re-pairing is the only way back. */
async function handleAuthLoss<T>(deps: Deps, result: Result<T>): Promise<Result<T>> {
  if (!result.ok && result.error.kind === 'AUTH_LOST') {
    await clearCredentials(deps.browser)
  }
  return result
}

/**
 * The groups the user can pick from.
 *
 * Filtered client-side because `GET /api/groups` returns every group on the
 * instance, including other people's personal ones. Without this the picker
 * would offer groups whose entries never load.
 */
export async function listGroups(deps: Deps): Promise<Result<GroupSummary[]>> {
  const resolved = await authenticated(deps)
  if (!resolved.ok) return resolved

  const session = await resolved.data.client.session()
  if (!session.ok) return handleAuthLoss(deps, session)

  const groups = await resolved.data.client.listGroups()
  if (!groups.ok) return handleAuthLoss(deps, groups)

  const userId = session.data.user_id
  const mine = filterGroupsForUser(groups.data, userId)

  await stampActivity(deps.browser, deps.clock.now())
  return ok(
    sortGroups(mine).map((group) => ({
      id: group.id,
      name: group.name,
      isPersonal: group.isPersonal,
      // Drives whether "Add password" is offered: the web app's ?create=1 only
      // opens the modal for an owner, so showing it otherwise would land the
      // user on a list with nothing happening.
      isOwner: isUserOwnerOf(group, userId),
    })),
  )
}

async function loadEntries(deps: Deps): Promise<Result<Entry[]>> {
  const cached = await deps.browser.session.get<CachedEntries>(SESSION_KEYS.entriesCache)
  const now = deps.clock.now()

  if (cached && now.getTime() - new Date(cached.fetchedAt).getTime() < ENTRIES_CACHE_TTL_MS) {
    return ok(cached.entries)
  }

  const resolved = await authenticated(deps)
  if (!resolved.ok) return resolved

  const entries = await resolved.data.client.listEntries()
  if (!entries.ok) return handleAuthLoss(deps, entries)

  await deps.browser.session.set(SESSION_KEYS.entriesCache, {
    entries: entries.data,
    fetchedAt: now.toISOString(),
  })
  await stampActivity(deps.browser, now)
  return ok(entries.data)
}

export async function listEntries(
  deps: Deps,
  groupId: string,
  query?: string,
): Promise<Result<{ entries: EntrySummary[]; hiddenCount: number }>> {
  const loaded = await loadEntries(deps)
  if (!loaded.ok) return loaded

  const visible = visibleEntriesForGroup(loaded.data, groupId, deps.clock.now())
  const matching = query
    ? visible.entries.filter((e) => matchesEntryQuery(e, query))
    : visible.entries

  return ok({ entries: matching.map(toSummary), hiddenCount: visible.hiddenCount })
}

/**
 * Autofill seam: candidates for a page, ranked.
 *
 * A pure filter over the cache. No API call, therefore no audit event, which is
 * what makes autofill compatible with the vault's audit log.
 */
export async function matchEntries(deps: Deps, pageUrl: string): Promise<Result<EntrySummary[]>> {
  const loaded = await loadEntries(deps)
  if (!loaded.ok) return loaded

  const groupId = (await deps.browser.local.get<string>(LOCAL_KEYS.selectedGroupId)) ?? null
  const pool = groupId
    ? visibleEntriesForGroup(loaded.data, groupId, deps.clock.now()).entries
    : loaded.data.filter((entry) => entry.canRead)

  const ranked = pool
    .map((entry) => ({ entry, quality: matchesDomain(entry.url, pageUrl) }))
    .filter((candidate) => candidate.quality !== 'none')
    .sort((left, right) => MATCH_RANK[right.quality] - MATCH_RANK[left.quality])

  return ok(ranked.map((candidate) => toSummary(candidate.entry)))
}

/**
 * Fetch one secret.
 *
 * Only ever called from an explicit user action: every call writes a
 * PasswordAccessedEvent in the vault's audit log.
 */
export async function revealSecret(deps: Deps, entryId: string): Promise<Result<string>> {
  const resolved = await authenticated(deps)
  if (!resolved.ok) return resolved

  const secret = await resolved.data.client.revealPassword(entryId)
  if (!secret.ok) return handleAuthLoss(deps, secret)

  await stampActivity(deps.browser, deps.clock.now())
  return secret
}

function toSummary(entry: Entry): EntrySummary {
  return {
    id: entry.id,
    name: entry.name,
    folder: entry.folder,
    login: entry.login,
    url: entry.url,
    groupId: entry.groupId,
    accessibleGroupIds: entry.accessibleGroupIds,
    canRead: entry.canRead,
    canWrite: entry.canWrite,
    accessExpiresAt: entry.accessExpiresAt,
  }
}

/**
 * Remember which group the popup should show.
 *
 * Stored rather than derived: the choice is the user's, and re-deriving a
 * default on every open would silently move the list under someone who picked
 * a non-default group.
 */
export async function selectGroup(deps: Deps, groupId: string): Promise<Result<ConnectionState>> {
  await deps.browser.local.set(LOCAL_KEYS.selectedGroupId, groupId)
  // The cached listing was filtered for the previous group.
  await deps.browser.session.remove(SESSION_KEYS.entriesCache)
  return getConnectionState(deps)
}
