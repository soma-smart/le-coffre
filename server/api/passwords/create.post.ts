import { z } from 'zod'
import { useDatabase } from '~/composables/useDatabase'


const createPasswordSchema = z.object({
    value: z.string().min(1, 'Le mot de passe ne peut pas être vide'),
})

export default defineEventHandler(async (event) => {
    try {
        const body = await readValidatedBody(event, (value) => createPasswordSchema.parse(value))

        const { createPassword } = useDatabase()
        const result = await createPassword(body.value)

        return {
            success: true,
            data: result[0]
        }
    } catch (error) {
        setResponseStatus(event, 400)
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Une erreur est survenue'
        }
    }
})