import { generate } from 'generate-password'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const passwordSize = parseInt(query.size as string) || 20
  return generate({
    length: passwordSize,
    numbers: true,
    symbols: true,
    uppercase: true,
    lowercase: true,
  })
})
