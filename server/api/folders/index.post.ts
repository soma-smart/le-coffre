import { requireAuth } from '~/server/utils/requireAuth'
import { schema } from '~/shared/schemas/newFolder'

export default defineEventHandler(async (event) => {
  const session = await requireAuth(event)
  if ('error' in session)
    return session

  const result = await readValidatedBody(event, body =>
    schema.safeParse(body))

  if (!result.success) {
    setResponseStatus(event, 400)
    return {
      success: false,
      error: 'Invalid input',
    }
  }

  console.log('tata')
  return 'toto'
})
