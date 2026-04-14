import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { listPasswordAccessPasswordsPasswordIdAccessGet } from '@/client/sdk.gen'
import type { GetPasswordListResponse } from '@/client/types.gen'
import { usePasswordsStore } from '@/stores/passwords'

const ACCESS_CACHE_DURATION = 30000
const pendingByPasswordId = new Map<string, Promise<string[]>>()
const requestVersionByPasswordId = new Map<string, number>()
let requestSequence = 0
let hydrateSequence = 0

export const usePasswordAccessStore = defineStore('passwordAccess', () => {
  const accessByPasswordId = ref<Record<string, string[]>>({})
  const lastFetchByPasswordId = ref<Record<string, number>>({})
  const passwordsStore = usePasswordsStore()

  const getAccessibleGroupIds = (passwordId: string, fallbackGroupId: string): string[] =>
    accessByPasswordId.value[passwordId] ?? [fallbackGroupId]

  const fetchPasswordAccess = async (
    passwordId: string,
    fallbackGroupId: string,
    force = false,
  ): Promise<string[]> => {
    const now = Date.now()
    const lastFetch = lastFetchByPasswordId.value[passwordId]

    if (!force && lastFetch && now - lastFetch < ACCESS_CACHE_DURATION) {
      return getAccessibleGroupIds(passwordId, fallbackGroupId)
    }

    const existingPendingPromise = pendingByPasswordId.get(passwordId)
    if (!force && existingPendingPromise) {
      return existingPendingPromise
    }

    const requestVersion = ++requestSequence
    requestVersionByPasswordId.set(passwordId, requestVersion)

    const pendingPromise = (async () => {
      try {
        const response = await listPasswordAccessPasswordsPasswordIdAccessGet({
          path: { password_id: passwordId },
        })

        const groupIds = [
          ...new Set((response.data?.group_access_list ?? []).map((item) => item.user_id)),
        ]
        const resolvedGroupIds = groupIds.length > 0 ? groupIds : [fallbackGroupId]

        if (requestVersionByPasswordId.get(passwordId) === requestVersion) {
          accessByPasswordId.value = {
            ...accessByPasswordId.value,
            [passwordId]: resolvedGroupIds,
          }
          lastFetchByPasswordId.value = {
            ...lastFetchByPasswordId.value,
            [passwordId]: Date.now(),
          }
        }

        return resolvedGroupIds
      } catch {
        const fallbackGroupIds = [fallbackGroupId]

        if (requestVersionByPasswordId.get(passwordId) === requestVersion) {
          accessByPasswordId.value = {
            ...accessByPasswordId.value,
            [passwordId]: fallbackGroupIds,
          }
          lastFetchByPasswordId.value = {
            ...lastFetchByPasswordId.value,
            [passwordId]: Date.now(),
          }
        }

        return fallbackGroupIds
      } finally {
        pendingByPasswordId.delete(passwordId)
      }
    })()

    pendingByPasswordId.set(passwordId, pendingPromise)
    return pendingPromise
  }

  const hydratePasswordAccess = async (
    passwords: GetPasswordListResponse[],
    force = false,
  ): Promise<void> => {
    const currentHydrateSequence = ++hydrateSequence

    if (passwords.length === 0) {
      accessByPasswordId.value = {}
      lastFetchByPasswordId.value = {}
      requestVersionByPasswordId.clear()
      return
    }

    await Promise.all(
      passwords.map((password) => fetchPasswordAccess(password.id, password.group_id, force)),
    )

    if (currentHydrateSequence !== hydrateSequence) {
      return
    }

    const visiblePasswordIds = new Set(passwords.map((password) => password.id))
    accessByPasswordId.value = Object.fromEntries(
      Object.entries(accessByPasswordId.value).filter(([passwordId]) =>
        visiblePasswordIds.has(passwordId),
      ),
    )
    lastFetchByPasswordId.value = Object.fromEntries(
      Object.entries(lastFetchByPasswordId.value).filter(([passwordId]) =>
        visiblePasswordIds.has(passwordId),
      ),
    )
  }

  const getAccessibleGroupIdsForPassword = (password: GetPasswordListResponse): string[] =>
    getAccessibleGroupIds(password.id, password.group_id)

  const passwordCountByGroupId = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {}

    for (const password of passwordsStore.passwords) {
      for (const groupId of getAccessibleGroupIdsForPassword(password)) {
        counts[groupId] = (counts[groupId] ?? 0) + 1
      }
    }

    return counts
  })

  const invalidatePasswordAccess = (passwordId?: string) => {
    if (!passwordId) {
      accessByPasswordId.value = {}
      lastFetchByPasswordId.value = {}
      pendingByPasswordId.clear()
      requestVersionByPasswordId.clear()
      return
    }

    const remainingAccess = { ...accessByPasswordId.value }
    delete remainingAccess[passwordId]

    const remainingTimestamps = { ...lastFetchByPasswordId.value }
    delete remainingTimestamps[passwordId]

    accessByPasswordId.value = remainingAccess
    lastFetchByPasswordId.value = remainingTimestamps
    pendingByPasswordId.delete(passwordId)
    requestVersionByPasswordId.delete(passwordId)
  }

  watch(
    () => passwordsStore.passwords,
    async (nextPasswords) => {
      await hydratePasswordAccess(nextPasswords)
    },
    { immediate: true },
  )

  return {
    accessByPasswordId,
    passwordCountByGroupId,
    fetchPasswordAccess,
    hydratePasswordAccess,
    getAccessibleGroupIds,
    getAccessibleGroupIdsForPassword,
    invalidatePasswordAccess,
  }
})
