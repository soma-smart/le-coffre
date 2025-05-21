import type { FolderItem } from '~/shared/types/folderItem'

export default defineEventHandler((_event) => {
  // Dummy return to mockup the API
  const folderItems: FolderItem[] = [
    {
      label: 'First folder',
      icon: 'i-lucide-folder',
      slug: 'first-folder',
      children: [
        {
          label: '1-1',
          slug: '1-1',
          icon: 'i-vscode-icons-file-type-typescript',
          children: [
            { label: 'useAuth.ts', icon: 'i-vscode-icons-file-type-typescript', slug: 'useAuth.ts' },
            { label: 'useUser.ts', icon: 'i-vscode-icons-file-type-typescript', slug: 'useUser.ts' },
          ],
        },
        {
          label: '1-2',
          slug: '1-2',
          children: [
            { label: '1-2-1', slug: '1-2-1', icon: 'i-vscode-icons-file-type-vue' },
            { label: '1-2-2', slug: '1-2-2', icon: 'i-vscode-icons-file-type-vue' },
          ],
        },
      ],
    },
    { label: 'Second folder', slug: 'second-folder', icon: 'i-lucide-folder', active: true },
    { label: 'Third folder', slug: 'third-folder', icon: 'i-lucide-folder' },
  ]

  return folderItems
})
