import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development the page is served by Vite (port 5173) and every /api call is passed on to FastAPI (port 8000),
// so the page always calls the same address it will have when FastAPI serves the built files.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
