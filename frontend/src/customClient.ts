// src/apiConfig.ts
import { client } from '@/client/client.gen';
// import error type from the generated SDK if available
import type { HttpValidationError } from '@/client/types.gen';
import router from '@/router';
import { useCsrfStore } from '@/stores/csrf';

// Apply runtime configuration (injected via /config.js before app load)
const runtimeConfig = (window as unknown as { __APP_CONFIG__?: { apiBaseUrl?: string } }).__APP_CONFIG__;
if (runtimeConfig?.apiBaseUrl) {
  client.setConfig({ baseUrl: runtimeConfig.apiBaseUrl });
}

// Configure CSRF token interceptor for mutating requests
client.interceptors.request.use(async (request, options) => {
  // Only add CSRF token for mutating methods
  const method = options.method?.toUpperCase();
  const mutateMethods = ['POST', 'PUT', 'DELETE', 'PATCH'];
  
  if (method && mutateMethods.includes(method)) {
    const csrfStore = useCsrfStore();
    const token = await csrfStore.getToken();
    
    if (token) {
      // Add CSRF token to request headers
      request.headers.set('X-CSRF-Token', token);
    }
  }
  
  return request;
});

// Configure the global error interceptor
client.interceptors.error.use(async (error: unknown, response: Response | undefined) => {
  // ── Rate Limiting (429) ──────────────────────────────────────
  if (response?.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    const seconds = retryAfter ? parseInt(retryAfter, 10) : 0;
    const detail = seconds > 0
      ? `Too many requests. Please try again in ${seconds} seconds.`
      : 'Too many requests. Please try again later.';

    // Dispatch a custom event so components can react (e.g. LoginForm countdown)
    window.dispatchEvent(
      new CustomEvent('rate-limited', { detail: { retryAfter: seconds } }),
    );

    // Show a global toast via PrimeVue's event bus
    import('primevue').then(({ useToast }) => {
      try {
        const toast = useToast();
        toast.add({
          severity: 'warn',
          summary: 'Rate Limited',
          detail,
          life: 5000,
        });
      } catch {
        // Toast not available outside component context — silently ignore
      }
    });

    return error;
  }

  // ── Authentication errors ────────────────────────────────────
  console.error('Global API Error Interceptor caught an error:', error);

  const errorDetail = (error as HttpValidationError).detail;
  const errorMessage = Array.isArray(errorDetail) ? errorDetail[0]?.msg : errorDetail;

  if (errorMessage === 'No authentication token provided') {
    localStorage.removeItem('login');
    await router.push({
      path: '/login',
      query: { redirect: router.currentRoute.value.fullPath, reason: 'no_token' }
    });
  }

  return error;
});

export { client };
