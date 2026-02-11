// Runtime configuration - loaded before the app starts
// In production (Kubernetes), this file is replaced by a ConfigMap mount
// allowing environment-specific configuration without rebuilding the image
window.__APP_CONFIG__ = {
  apiBaseUrl: '/api'
};
