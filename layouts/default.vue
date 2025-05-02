<template>
  <div class="flex h-screen">
    <!-- Menu Component -->
    <div class="flex flex-col h-full p-4 shadow-lg bg-(--ui-bg-elevated) border-r border-(--ui-border)">
      <!-- Logo -->
      <NuxtLink to="/" class="p-4">
        <div class="flex items-center space-x-2">
          <h1
            class="text-2xl font-bold bg-gradient-to-r from-primary-600 via-primary-600 to-primary-500 text-transparent bg-clip-text"
          >
            Le Coffre
          </h1>
          <UIcon
            name="i-lucide-vault"
            class="text-3xl text-primary-500 dark:text-primary-500"
          />
        </div>
      </NuxtLink>

      <hr class="mb-4 border-(--ui-border)">
      <!-- Top Menu (content at the top) -->
      <MenuTop />

      <!-- Bottom Menu (pushes to the bottom) -->
      <div class="mt-auto">
        <div class="flex justify-center mb-4">
          <ThemeSwitcher />
        </div>
        <hr class="my-2 border-(--ui-border)">
        <MenuBottom />
        <hr class="my-2 border-(--ui-border)">
        <MenuUserButton />
      </div>
    </div>

    <!-- Slot Content -->
    <div class="flex-1 p-4">
      <slot />
    </div>
  </div>
</template>
