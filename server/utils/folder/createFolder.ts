import { consola } from 'consola'
import { folder } from '~/server/database/schema'
import { useDatabase } from '~/server/utils/useDatabase'
import { generateUniqueSlug } from '~/server/utils/folder/generateSlug'

export const createFolderService = {
  async createFolder(userId: string, name: string) {
    try {
      const slug = await generateUniqueSlug(name)

      await useDatabase().insert(folder).values({
        owner_id: userId,
        name,
        slug,
        icon: 'i-lucide-folder',
        color: '#4f46e5',
      }).returning()

      return {
        success: true,
      }
    }
    catch (error) {
      consola.error('Error creating folder:', error)
      throw error
    }
  },
}
