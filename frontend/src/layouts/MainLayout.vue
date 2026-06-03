<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { computed } from 'vue'

const router = useRouter()
const route = useRoute()

const isPasswordsActive = computed(() => route.path === '/' || route.path.startsWith('/passwords/'))
const isGroupsActive = computed(() => route.path === '/groups')
const isProfileActive = computed(() => route.path === '/profile')
</script>

<template>
  <div class="h-screen flex overflow-hidden">
    <!-- Menu latéral -->
    <aside class="hidden md:flex w-80 border-r border-surface flex flex-col">
      <div class="p-4 border-b border-surface flex items-center gap-3">
        <img src="/img/le-coffre.png" alt="Le Coffre" class="h-10 w-auto" />
        <h1 class="text-2xl font-bold text-primary">Le Coffre</h1>
      </div>
      <div class="flex-1 overflow-y-auto">
        <MainMenu />
      </div>
    </aside>

    <!-- Contenu principal -->
    <div class="flex-1 flex flex-col min-w-0">
      <main class="flex-1 p-6 overflow-y-auto overflow-x-hidden pb-16 md:pb-0">
        <slot />
      </main>
    </div>
  </div>

  <!-- Barre de navigation (mobile uniquement) -->
  <nav class="md:hidden fixed bottom-0 left-0 right-0 border-t border-surface bg-surface-0 flex">
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
