import { authClient } from '~/server/utils/auth-client'

export async function signOut() {
  const router = useRouter()
  const toast = useToast()

  await authClient.signOut({
    fetchOptions: {
      onSuccess: () => {
        router.push('/login')
        toast.add({ title: 'Logout', description: 'You have been logged out.', color: 'success' })
      },
    },
  })
}
