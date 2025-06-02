import { schema } from '~/shared/schemas/newFolder'

export default defineEventHandler(async (event) => {
  // TODO: protect this endpoint with authentication
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
