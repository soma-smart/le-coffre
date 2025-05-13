import { authClient } from '~/utils/auth-client'

export async function signOut() {
  const toast = useToast()

  await authClient.signOut({
    fetchOptions: {
      onSuccess: async () => {
        await navigateTo('/login')
        toast.add({ title: 'Logout', description: 'You have been logged out.', color: 'success' })
      },
    },
  })
}
