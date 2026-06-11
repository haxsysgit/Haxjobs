import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// HaxJobs Dashboard
// Dev: npx vite --port 5173 --host 0.0.0.0
// Build: npx vite build -> dashboard/dist/
// Python API serves dashboard/dist/ when present.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8800',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
