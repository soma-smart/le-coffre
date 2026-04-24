import { ref } from 'vue'
import { defineStore } from 'pinia'

const ADMIN_PASSWORD_VIEW_KEY = 'lecoffre.admin-password-view'

export const useAdminPasswordViewStore = defineStore('adminPasswordView', () => {
  const adminPasswordViewEnabled = ref(false)
  const loaded = ref(false)

  const loadAdminPasswordView = () => {
    if (loaded.value) return

    if (typeof window === 'undefined') {
      loaded.value = true
      return
    }

    adminPasswordViewEnabled.value = localStorage.getItem(ADMIN_PASSWORD_VIEW_KEY) === '1'
    loaded.value = true
  }

  const setAdminPasswordViewEnabled = (enabled: boolean) => {
    adminPasswordViewEnabled.value = enabled

    if (typeof window === 'undefined') return

    if (enabled) {
      localStorage.setItem(ADMIN_PASSWORD_VIEW_KEY, '1')
    } else {
      localStorage.removeItem(ADMIN_PASSWORD_VIEW_KEY)
    }
  }

  return {
    adminPasswordViewEnabled,
    loadAdminPasswordView,
    setAdminPasswordViewEnabled,
  }
})
