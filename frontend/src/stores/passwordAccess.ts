import { computed } from 'vue'
import { defineStore } from 'pinia'
import { accessibleGroupIdsFor } from '@/domain/password/Password'
import { usePasswordsStore } from '@/stores/passwords'

export const usePasswordAccessStore = defineStore('passwordAccess', () => {
  const passwordsStore = usePasswordsStore()

  const passwordCountByGroupId = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {}

    for (const password of passwordsStore.passwords) {
      for (const groupId of accessibleGroupIdsFor(password)) {
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
    invalidatePasswordAccess,
  }
})
