// src/apiConfig.ts
import { client } from '@/client/client.gen';
// import error type from the generated SDK if available
import type { HttpValidationError } from '@/client/types.gen';
import router from '@/router';

// Apply runtime configuration (injected via /config.js before app load)
const runtimeConfig = (window as unknown as { __APP_CONFIG__?: { apiBaseUrl?: string } }).__APP_CONFIG__;
if (runtimeConfig?.apiBaseUrl) {
  client.setConfig({ baseUrl: runtimeConfig.apiBaseUrl });
}

// Configure the global error interceptor
client.interceptors.error.use(async (error: unknown) => {
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
