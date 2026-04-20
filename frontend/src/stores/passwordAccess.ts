import { computed } from 'vue'
import { defineStore } from 'pinia'
import type { Password } from '@/domain/password/Password'
import { usePasswordsStore } from '@/stores/passwords'

export const usePasswordAccessStore = defineStore('passwordAccess', () => {
  const passwordsStore = usePasswordsStore()

  const getAccessibleGroupIdsForPassword = (password: Password): string[] =>
    password.accessibleGroupIds.length > 0 ? password.accessibleGroupIds : [password.groupId]

  const passwordCountByGroupId = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {}

    for (const password of passwordsStore.passwords) {
      for (const groupId of getAccessibleGroupIdsForPassword(password)) {
        counts[groupId] = (counts[groupId] ?? 0) + 1
      }
    }

    return counts
  })

  const invalidatePasswordAccess = () => {
    passwordsStore.invalidateCache()
  }

  return {
    passwordCountByGroupId,
    getAccessibleGroupIdsForPassword,
    invalidatePasswordAccess,
  }
})
