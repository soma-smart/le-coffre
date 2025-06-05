// server/utils/requireAuth.ts
import type { H3Event } from 'h3'
import { auth } from '~/server/config/auth'

export async function requireAuth(event: H3Event) {
  const session = await auth.api.getSession({ headers: event.headers })

  if (!session || !session.user) {
    setResponseStatus(event, 401)
    return {
      error: 'User not authenticated',
    }
  }

  return session
}
