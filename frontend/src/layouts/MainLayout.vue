<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { computed } from 'vue'
import { useResizableWidth } from '@/composables/useResizableWidth'

withDefaults(defineProps<{ padded?: boolean }>(), { padded: true })

const router = useRouter()
const route = useRoute()

const isPasswordsActive = computed(() => route.path === '/' || route.path.startsWith('/passwords/'))
const isGroupsActive = computed(() => route.path === '/groups')
const isProfileActive = computed(() => route.path === '/profile')

const { width: sidebarWidth, startResizing: startSidebarResizing } = useResizableWidth({
  storageKey: 'le-coffre.sidebar-width',
  defaultWidth: 320,
  min: 220,
  max: 480,
})
</script>

<template>
  <div class="h-screen flex overflow-hidden">
    <!-- Sidebar menu -->
    <aside
      class="hidden md:flex relative shrink-0 border-r border-surface flex-col"
      :style="{ width: `${sidebarWidth}px` }"
    >
      <div class="h-18 px-4 border-b border-surface flex items-center gap-3">
        <img src="/img/le-coffre.png" alt="Le Coffre" class="h-10 w-auto" />
        <h1 class="text-2xl font-bold text-primary">Le Coffre</h1>
      </div>
      <div class="flex-1 min-h-0 flex">
        <MainMenu />
      </div>
      <ResizeHandle @pointerdown="startSidebarResizing" />
    </aside>

    <!-- Main content -->
    <div class="flex-1 flex flex-col min-w-0">
      <main
        class="flex-1 overflow-x-hidden pb-16 md:pb-0"
        :class="padded ? 'p-6 overflow-y-auto' : 'overflow-hidden'"
      >
        <slot />
      </main>
    </div>
  </div>

  <!-- Navigation bar (mobile only) -->
  <nav
    class="md:hidden fixed bottom-0 left-0 right-0 border-t border-surface bg-surface-0 dark:bg-surface-900 flex"
  >
    <button
      @click="router.push('/')"
      class="flex-1 flex flex-col items-center py-3 gap-1"
      :class="isPasswordsActive ? 'text-primary' : 'text-muted-color'"
    >
      <span class="pi pi-key text-xl" />
      <span class="text-xs">Passwords</span>
    </button>

    <button
      @click="router.push('/groups')"
      class="flex-1 flex flex-col items-center py-3 gap-1"
      :class="isGroupsActive ? 'text-primary' : 'text-muted-color'"
    >
      <span class="pi pi-users text-xl" />
      <span class="text-xs">Groups</span>
    </button>

    <button
      @click="router.push('/profile')"
      class="flex-1 flex flex-col items-center py-3 gap-1"
      :class="isProfileActive ? 'text-primary' : 'text-muted-color'"
    >
      <span class="pi pi-user text-xl" />
      <span class="text-xs">Profile</span>
    </button>
  </nav>
</template>
