import * as z from 'zod'

export const schema = z.object({
  name: z.string(),
})

export type Schema = z.output<typeof schema>
