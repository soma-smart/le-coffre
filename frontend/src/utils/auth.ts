/**
 * Check if the user is authenticated
 * Checks for the 'logged_in' cookie that is set alongside httpOnly JWT cookies
 */
export function isAuthenticated(): boolean {
  return getCookie('logged_in') === 'true';
}

/**
 * Get a specific cookie value by name
 */
export function getCookie(name: string): string | null {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [cookieName, cookieValue] = cookie.trim().split('=');
    if (cookieName === name) {
      return decodeURIComponent(cookieValue);
    }
  }
  return null;
}
