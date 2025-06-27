import { consola } from 'consola'
import { requireAuth } from '~/server/utils/requireAuth'
import { newFolderSchema } from '~/shared/schemas/newFolder'
import { createFolderService } from '~/server/utils/folder/createFolder'

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
    const response = await createFolderService.createFolder(session.user.id, name)

    return response
  }
  catch (error) {
    consola.error('Error handling folder creation request:', error)
    setResponseStatus(event, 500)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to create folder',
      stack: error instanceof Error ? error.stack : undefined,
    }
  }
})
