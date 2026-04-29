import { ref } from 'vue'
import { defineStore } from 'pinia'
import { useContainer } from '@/plugins/container'
import { PREFERENCE_KEYS } from '@/domain/preferences/Preference'

export const useAdminPasswordViewStore = defineStore('adminPasswordView', () => {
  // Resolve use cases at setup time — inject() has no component context
  // inside Pinia async actions.
  const { preferences } = useContainer()

  const adminPasswordViewEnabled = ref(false)
  const loaded = ref(false)

  const loadAdminPasswordView = () => {
    if (loaded.value) return
    const stored = preferences.read.execute<boolean>({
      key: PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED,
    })
    adminPasswordViewEnabled.value = stored === true
    loaded.value = true
  }

  const setAdminPasswordViewEnabled = (enabled: boolean) => {
    adminPasswordViewEnabled.value = enabled
    if (enabled) {
      preferences.write.execute({
        key: PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED,
        value: true,
      })
    } else {
      preferences.remove.execute({ key: PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED })
    }
  }

  /**
   * Reset in-memory + persisted state on logout. Same SPA tab can host
   * multiple sessions; user A's admin-view toggle must not stick around
   * for user B.
   */
  const clear = () => {
    preferences.remove.execute({ key: PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED })
    adminPasswordViewEnabled.value = false
    loaded.value = false
  }

  return {
    adminPasswordViewEnabled,
    loadAdminPasswordView,
    setAdminPasswordViewEnabled,
    clear,
  }
})
