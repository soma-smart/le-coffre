<script setup lang="ts">
import type { ContextMenuItem, TreeItem } from '@nuxt/ui'
import { ref } from 'vue'

const router = useRouter()

// Extends TreeItem to include 'id' property
interface FolderItem extends TreeItem {
  label: string
  slug?: string
}

const items = ref<FolderItem[]>([
  {
    label: 'First folder',
    defaultExpanded: true,
    children: [
      {
        label: '1-1',
        icon: 'i-vscode-icons-file-type-typescript',
        children: [
          { label: 'useAuth.ts', icon: 'i-vscode-icons-file-type-typescript' },
          { label: 'useUser.ts', icon: 'i-vscode-icons-file-type-typescript' },
        ],
      },
      {
        label: '1-2',
        defaultExpanded: true,
        children: [
          { label: '1-2-1', icon: 'i-vscode-icons-file-type-vue' },
          { label: '1-2-2', icon: 'i-vscode-icons-file-type-vue' },
        ],
      },
    ],
  },
  { label: 'Second folder', icon: 'i-vscode-icons-file-type-vue' },
  { label: 'Third folder', icon: 'i-vscode-icons-file-type-nuxt' },
])

const menuItems = ref<ContextMenuItem[][]>([
  [
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
  currentItems: FolderItem[] = items.value,
  path: string[] = [],
): string[] | null {
  for (const node of currentItems) {
    const newPath = [...path, node.label]

    // Match item by label and children structure to be safer than by reference
    if (node.label === item.label && node.children === item.children)
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
    console.log(`Going to /passwords/${encodedPath}`)
    router.push(`/passwords/${encodedPath}`)
  }
}
</script>

<template>
  <UTree :items="items">
    <template #item="{ item, expanded }">
      <div class="flex items-center justify-between w-full rounded-xl transition-colors">
        <!-- Left: Context menu trigger + icons -->
        <div class="flex items-center w-full">
          <UContextMenu :items="menuItems">
            <div
              class="flex items-center p-3 cursor-pointer hover:bg-gray-100 rounded-xl w-full"
              @click="handleItemClick(item)"
            >
              <UIcon v-if="expanded" name="i-lucide-folder-open" />
              <UIcon v-else name="i-lucide-folder" />
              <span class="ml-2 flex items-center">
                {{ item.label }}
                <UIcon v-if="item.icon" :name="item.icon" class="text-lg ml-2" />
              </span>
            </div>
          </UContextMenu>
        </div>

        <!-- Right: Chevron for expanding/collapsing -->
        <UIcon
          v-if="item.children" name="i-lucide-chevron-down"
          class="w-4 h-4 mr-3 transform transition-transform duration-200" :class="[{ 'rotate-180': expanded }]"
        />
      </div>
    </template>
  </UTree>
</template>
