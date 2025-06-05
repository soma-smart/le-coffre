import * as z from 'zod'

export const newFolderSchema = z.object({
  name: z.string().min(1, 'Folder name is required')
    .max(100, 'Folder name must be less than 100 characters'),
})

export type Schema = z.output<typeof newFolderSchema>
