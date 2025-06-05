import { consola } from 'consola'
import { requireAuth } from '~/server/utils/requireAuth'
import { newFolderSchema } from '~/shared/schemas/newFolder'
import { generateUniqueSlug } from '~/server/utils/folder/generateSlug'
import { folder } from '~/server/database/schema'
import { useDatabase } from '~/server/utils/useDatabase'

export default defineEventHandler(async (event) => {
  try {
    const session = await requireAuth(event)
    if ('error' in session) {
      return session
    }

    const result = await readValidatedBody(event, body =>
      newFolderSchema.safeParse(body))

    if (!result.success) {
      setResponseStatus(event, 400)
      return {
        success: false,
        error: 'Invalid input',
        details: result.error.format(),
      }
    }

    const { name } = result.data

    const slug = await generateUniqueSlug(name)

    const insertResult = await useDatabase().insert(folder).values({
      owner_id: session.user.id,
      name,
      slug,
      icon: 'i-lucide-folder',
      color: '#4f46e5',
    }).returning()

    return {
      success: true,
      inserted: insertResult,
    }
  }
  catch (error) {
    consola.error('Error creating folder:', error)
    setResponseStatus(event, 500)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to create folder',
      stack: error instanceof Error ? error.stack : undefined,
    }
  }
})
