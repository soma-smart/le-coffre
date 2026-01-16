import { useUserStore } from '@/stores/user';

/**
 * Logout utility - clears all authentication cookies and localStorage
 */
export function logout(): void {
  // Clear the logged_in cookie by setting it to expire in the past
  document.cookie = 'logged_in=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=lax';
  
  // Clear user store
  const userStore = useUserStore();
  userStore.clearUser();
}
