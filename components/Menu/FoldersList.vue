<script setup lang="ts">
import type { ContextMenuItem } from '@nuxt/ui'
import { ref } from 'vue'

const route = useRoute()
const router = useRouter()

const { data, pending, error } = await useFetch<FolderItem[]>('/api/folders/list')

/**
 * Annotate each folder item with:
 *  - active: true iff its fullPath === slug
 *  - defaultOpen: true if any descendant isActive
 *  - children: recursively processed
 */
function annotateActive(
  items: FolderItem[],
  slug: string[],
  parentPath: string[] = [],
): (FolderItem & { active: boolean, defaultOpen?: boolean, children?: any })[] {
  return items.map((item) => {
    const fullPath = [...parentPath, item.slug]

    // First process children so we know if any of them (or their descendants) are active
    const children = item.children
      ? annotateActive(item.children as FolderItem[], slug, fullPath)
      : undefined

    // Check exact match for this node
    const isActive
      = slug.length === fullPath.length && slug.every((seg, i) => seg === fullPath[i])

    // If any child (or deeper descendant) is active, this node should defaultOpen
    const isAncestorOpen = !!children?.some(child => child.active || child.defaultOpen)

    return {
      ...item,
      active: isActive,
      // only add defaultOpen if this node has children and one of them is active/ancestor
      ...(children ? { defaultOpen: isAncestorOpen } : {}),
      children,
    }
  })
}

const items = computed(() => {
  const slug = Array.isArray(route.params.slug)
    ? (route.params.slug as string[])
    : []
  return data.value ? annotateActive(data.value, slug) : []
})

const menuItems = ref<ContextMenuItem[][]>([
  [
    { label: 'New folder', icon: 'i-lucide-plus', disabled: true },
    {
      label: 'Appearance',
      children: [
        { label: 'System', icon: 'i-lucide-monitor' },
        { label: 'Light', icon: 'i-lucide-sun' },
        { label: 'Dark', icon: 'i-lucide-moon' },
      ],
    },
  ],
  [
    { label: 'Rename', kbds: ['ctrl', 'r'], disabled: true },
    { label: 'Permissions', kbds: ['shift', 'meta', 'd'] },
    { label: 'Show properties', disabled: true },
  ],
  [{ label: 'Delete', icon: 'i-lucide-trash' }],
])

/**
 * Recursively build path to item
 */
function buildItemPath(
  item: FolderItem,
  currentItems: FolderItem[] = data.value ?? [],
  path: string[] = [],
): string[] | null {
  for (const node of currentItems) {
    const newPath = [...path, node.slug]

    if (node.slug === item.slug && node.children === item.children)
      return newPath

    if (node.children) {
      const result = buildItemPath(item, node.children as FolderItem[], newPath)
      if (result)
        return result
    }
  }
  return null
}

function handleItemClick(item: any) {
  const fullPath = buildItemPath(item)
  if (fullPath) {
    const encodedPath = fullPath.map(encodeURIComponent).join('/')
    router.push(`/passwords/${encodedPath}`)
  }
}
</script>

<template>
  <div v-if="pending">
    <UProgress orientation="vertical" class="h-48" />
  </div>
  <div v-else-if="error">
    Error: {{ error.message }}
  </div>
  <UNavigationMenu orientation="vertical" :items="items" class="data-[orientation=vertical]:w-48">
    <template #item="{ item }">
      <UContextMenu :items="menuItems" @click="handleItemClick(item)">
        <div
          class="group flex items-center justify-between w-full cursor-pointer px-2 py-1 rounded-md transition-colors"
          @click="handleItemClick(item)"
        >
          <!-- Left: folder icon + label -->
          <div class="flex items-center space-x-2">
            <UIcon v-if="item.icon" :name="item.icon" class="text-lg" />
            <span class="flex items-center space-x-1">
              <span>{{ item.label }}</span>
            </span>
          </div>

          <!-- Right: chevron, rotates via the same data-state -->
          <UIcon
            v-if="item.children" name="i-lucide-chevron-down"
            class="w-4 h-4 transform transition-transform duration-200 data-[state=open]:rotate-180"
          />
        </div>
      </UContextMenu>
    </template>
  </UNavigationMenu>
</template>
