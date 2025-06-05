import { eq } from 'drizzle-orm'
import type { FolderItem } from '~/shared/types/folderItem'
import { folder } from '~/server/database/schema'

export default defineEventHandler(async (event) => {
  const session = await requireAuth(event)
  if ('error' in session) {
    return session
  }

  // Récupération des dossiers depuis la base de données
  const folders = await useDatabase().select().from(folder).where(eq(folder.owner_id, session.user.id))

  // Construct folder tree structure
  function buildFolderTree(folders: any[]): FolderItem[] {
    const folderMap = new Map()
    const rootFolders: FolderItem[] = []

    // First : create all objects FolderItem
    folders.forEach((folder) => {
      const folderItem: FolderItem = {
        label: folder.name,
        icon: folder.icon,
        slug: folder.slug,
        children: [],
      }
      folderMap.set(folder.id, folderItem)
    })

    // Second : construct the tree structure
    folders.forEach((folder) => {
      const folderItem = folderMap.get(folder.id)

      if (folder.parent_id == null) {
        // Root folder
        rootFolders.push(folderItem)
      }
      else {
        // Child folder
        const parentFolder = folderMap.get(folder.parent_id)
        if (parentFolder) {
          parentFolder.children.push(folderItem)
        }
      }
    })

    return rootFolders
  }

  // Build the folder tree structure
  const folderItems: FolderItem[] = buildFolderTree(folders)
  return folderItems
})
