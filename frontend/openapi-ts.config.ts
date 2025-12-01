import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'http://backend:8000/api/openapi.json',
  output: 'src/client',
  baseUrl: '/',
});
