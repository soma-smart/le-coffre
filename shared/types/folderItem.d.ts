import type { NavigationMenuItem } from '@nuxt/ui'

export interface FolderItem extends NavigationMenuItem {
  label: string
  slug: string
  icon?: string
  children?: FolderItem[]
};
