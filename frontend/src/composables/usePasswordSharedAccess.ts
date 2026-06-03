import { ref, watch, type Ref } from 'vue'
import type { Group } from '@/domain/group/Group'
import type { Password, PasswordEvent } from '@/domain/password/Password'

export interface SharedAccessInfo {
  occurredOn: string
  actorUsername: string
}

export interface PasswordEventsUseCases {
  listEvents: {
    execute(command: {
      passwordId: string
      eventTypes?: string[]
    }): Promise<readonly PasswordEvent[]>
  }
}

export interface UserUseCases {
  get: { execute(command: { userId: string }): Promise<{ username: string }> }
}

export interface UsePasswordSharedAccessOptions {
  /** The password we're rendering. */
  password: Ref<Password>
  /** Group id the card is currently rendered under, if any. */
  contextGroupId: Ref<string | undefined>
  /** Whether the user can write the password in this context. */
  canWriteInContext: Ref<boolean>
  /** Groups the current user belongs to (owner or member). */
  userBelongingGroups: Ref<readonly Group[]>
  /** Use case wrappers — injected so tests don't need a container. */
  passwords: PasswordEventsUseCases
  users: UserUseCases
  /**
   * Optional cache for actor → username lookups. Defaults to a fresh Map per
   * composable, but consumers can share a global cache to dedupe across
   * mounted cards.
   */
  actorUsernameCache?: Map<string, string>
}

function getEventDataString(eventData: Record<string, unknown>, key: string): string | null {
  const value = eventData[key]
  return typeof value === 'string' ? value : null
}

/**
 * Resolves the most recent `PasswordSharedEvent` whose `sharedWithGroupId`
 * matches the rendering context (a specific group, or any group the user
 * belongs to), then attaches the actor's username for display.
 *
 * Idempotent: re-runs whenever password id, write capability, context group,
 * or user-belonging groups change. Uses a version counter to drop stale fetches
 * when the inputs change mid-flight.
 */
export function usePasswordSharedAccess(options: UsePasswordSharedAccessOptions) {
  const sharedAccessInfo = ref<SharedAccessInfo | null>(null)
  const cache = options.actorUsernameCache ?? new Map<string, string>()
  let loadVersion = 0

  async function resolveActorUsername(userId: string, fallback: string | null): Promise<string> {
    const cached = cache.get(userId)
    if (cached) return cached

    try {
      const user = await options.users.get.execute({ userId })
      const username = user.username || fallback || 'Unknown user'
      cache.set(userId, username)
      return username
    } catch {
      return fallback || 'Unknown user'
    }
  }

  async function load(): Promise<void> {
    const currentVersion = ++loadVersion
    sharedAccessInfo.value = null

    if (options.canWriteInContext.value) return

    const targetGroupId = options.contextGroupId.value
    if (!targetGroupId) {
      const belongingIds = new Set(options.userBelongingGroups.value.map((g) => g.id))
      if (belongingIds.size === 0) return
    }

    if (targetGroupId && targetGroupId === options.password.value.groupId) return

    try {
      const events = await options.passwords.listEvents.execute({
        passwordId: options.password.value.id,
        eventTypes: ['PasswordSharedEvent'],
      })

      const matching = events
        .filter((e) => e.eventType === 'PasswordSharedEvent')
        .filter((e) => {
          const sharedWithGroupId = getEventDataString(e.eventData, 'sharedWithGroupId')
          if (!sharedWithGroupId) return false
          if (targetGroupId) return sharedWithGroupId === targetGroupId
          return options.userBelongingGroups.value.some((g) => g.id === sharedWithGroupId)
        })
        .sort((a, b) => new Date(b.occurredOn).getTime() - new Date(a.occurredOn).getTime())[0]

      if (!matching || currentVersion !== loadVersion) return

      const actorUsername = await resolveActorUsername(matching.actorUserId, matching.actorEmail)
      if (currentVersion !== loadVersion) return

      sharedAccessInfo.value = { occurredOn: matching.occurredOn, actorUsername }
    } catch (error) {
      console.error('Error loading shared access info:', error)
    }
  }

  watch(
    [
      () => options.password.value.id,
      options.canWriteInContext,
      options.contextGroupId,
      options.userBelongingGroups,
    ],
    () => {
      void load()
    },
    { immediate: true },
  )

  return { sharedAccessInfo, reload: load }
}
