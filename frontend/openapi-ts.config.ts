import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'http://backend:8123/api/openapi.json',
  output: 'src/client',
});