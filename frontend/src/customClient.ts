// src/apiConfig.ts
import { client } from '@/client/client.gen'
import router from '@/router'
import { useCsrfStore } from '@/stores/csrf'
import { logout } from '@/utils/logout'

// Apply runtime configuration (injected via /config.js before app load)
const runtimeConfig = (window as unknown as { __APP_CONFIG__?: { apiBaseUrl?: string } })
  .__APP_CONFIG__
if (runtimeConfig?.apiBaseUrl) {
  client.setConfig({ baseUrl: runtimeConfig.apiBaseUrl })
}

// ── Token Refresh State ──────────────────────────────────────────────────────
// Coalesces concurrent 401s into a single refresh call. Subsequent callers
// subscribe and receive the same result once the in-flight call completes.
let isRefreshing = false
let refreshSubscribers: Array<(success: boolean) => void> = []

function notifyTokenRefreshSubscribers(success: boolean): void {
  refreshSubscribers.forEach((cb) => cb(success))
  refreshSubscribers = []
}

/**
 * Attempt to refresh the access token using the HTTP-only refresh_token cookie.
 *
 * Security properties:
 * - The refresh_token value is stored in an HTTP-only cookie and is never
 *   readable by JavaScript. The browser sends it automatically.
 * - The new access_token is set as an HTTP-only cookie by the server; its
 *   value never passes through JavaScript.
 * - The refresh endpoint is CSRF-exempt on the backend (it uses the
 *   refresh_token cookie itself as the credential, not a CSRF token).
 */
async function attemptTokenRefresh(): Promise<boolean> {
  if (isRefreshing) {
    // A refresh is already in flight — subscribe and wait for its result
    return new Promise<boolean>((resolve) => {
      refreshSubscribers.push(resolve)
    })
  }

  isRefreshing = true
  try {
    const response = await fetch('/api/auth/refresh-token', {
      method: 'POST',
      credentials: 'include', // Sends the HTTP-only refresh_token cookie
    })
    const success = response.ok
    notifyTokenRefreshSubscribers(success)
    return success
  } catch {
    notifyTokenRefreshSubscribers(false)
    return false
  } finally {
    isRefreshing = false
  }
}

export { attemptTokenRefresh }

// ── CSRF Request Interceptor ─────────────────────────────────────────────────
client.interceptors.request.use((request, options) => {
  // Only add CSRF token for mutating methods
  const method = options.method?.toUpperCase()
  const mutateMethods = ['POST', 'PUT', 'DELETE', 'PATCH']

  if (method && mutateMethods.includes(method)) {
    const csrfStore = useCsrfStore()
    // Only use an already-cached token — never auto-fetch from within a request
    // interceptor, as that would trigger a second request (and its own error
    // handling) before the current request completes, causing race conditions
    // during login (when no token exists yet).
    // The token is explicitly fetched right after a successful login/SSO callback.
    const token = csrfStore.csrfToken

    if (token) {
      request.headers.set('X-CSRF-Token', token)
    }
  }

  return request
})

// ── Auto-Refresh Response Interceptor ────────────────────────────────────────
// On a 401, silently refreshes the access token (using the HTTP-only
// refresh_token cookie) and retries the original request transparently.
// If the refresh itself fails the session is torn down and the user is
// redirected to the login page.
client.interceptors.response.use(async (response: Response, request: Request, opts: unknown) => {
  if (response.status !== 401) {
    return response
  }

  // Never retry auth calls themselves — prevents infinite refresh loops
  const url = request.url
  if (url.includes('/auth/refresh-token') || url.includes('/auth/login')) {
    return response
  }

  const refreshSucceeded = await attemptTokenRefresh()

  if (refreshSucceeded) {
    // Rebuild and retry the original request.
    // - request.headers is not a consumed stream; safe to forward as-is.
    // - opts.serializedBody is the already-JSON-encoded body string that the
    //   SDK keeps on the options object, so it is available even after the
    //   original ReadableStream was consumed by the first fetch call.
    const resolvedOpts = opts as { serializedBody?: string }
    const retryInit: RequestInit = {
      method: request.method,
      headers: request.headers,
      credentials: 'include',
      redirect: 'follow',
    }
    if (resolvedOpts.serializedBody !== undefined) {
      retryInit.body = resolvedOpts.serializedBody
    }
    return fetch(request.url, retryInit)
  }

  // Refresh failed — tear down local session state and redirect to login
  if (router.currentRoute.value.path !== '/login') {
    logout()
    await router.push({
      path: '/login',
      query: { redirect: router.currentRoute.value.fullPath, reason: 'session_expired' },
    })
  }

  return response
})

// ── Global Error Interceptor ─────────────────────────────────────────────────
client.interceptors.error.use(async (error: unknown, response: Response | undefined) => {
  // ── Rate Limiting (429) ──────────────────────────────────────
  if (response?.status === 429) {
    const retryAfter = response.headers.get('Retry-After')
    const seconds = retryAfter ? parseInt(retryAfter, 10) : 0
    const detail =
      seconds > 0
        ? `Too many requests. Please try again in ${seconds} seconds.`
        : 'Too many requests. Please try again later.'

    // Dispatch a custom event so components can react (e.g. LoginForm countdown)
    window.dispatchEvent(new CustomEvent('rate-limited', { detail: { retryAfter: seconds } }))

    // Show a global toast via PrimeVue's event bus
    import('primevue').then(({ useToast }) => {
      try {
        const toast = useToast()
        toast.add({
          severity: 'warn',
          summary: 'Rate Limited',
          detail,
          life: 5000,
        })
      } catch {
        // Toast not available outside component context — silently ignore
      }
    })

    return error
  }

  // ── Unexpected Auth Errors ────────────────────────────────────
  // 401 responses are normally handled by the response interceptor above
  // (token refresh + redirect). This is a safety net for any that slip through.
  if (response?.status === 401 && router.currentRoute.value.path !== '/login') {
    logout()
    await router.push({
      path: '/login',
      query: { redirect: router.currentRoute.value.fullPath, reason: 'session_expired' },
    })
  }

  return error
})

export { client }
