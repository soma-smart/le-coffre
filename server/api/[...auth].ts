import { auth } from '~/server/config/auth'

export default defineEventHandler((event) => {
  return auth.handler(toWebRequest(event))
})
