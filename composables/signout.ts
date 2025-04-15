import { authClient } from "~/utils/auth-client"

export const signOut = async () => {
  const router = useRouter()
  const toast = useToast()

  await authClient.signOut({
    fetchOptions: {
      onSuccess: () => {
        router.push("/login")
        toast.add({ title: 'Logout', description: 'You have been logged out.', color: 'success' })
      },
    },
  });
}