import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['localhost', '127.0.0.1', 'host.docker.internal'],
    // Allow importing the repo's docs/*.md (one level above the frontend root)
    // as the single source of truth for the in-app /docs route.
    fs: { allow: ['..'] },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // FastAPI's Swagger UI (served at /api/docs) fetches the spec from the
      // root-absolute /openapi.json. In prod nginx rewrites that to
      // /api/openapi.json; in dev we proxy it straight through so the API
      // reference renders instead of parsing the SPA's index.html.
      // (We do NOT proxy /docs — that's the in-app documentation SPA route.)
      '/openapi.json': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
