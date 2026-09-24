import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development the API is reached through this proxy, so the browser only ever
// talks to one origin and no CORS setup is needed. The target uses 127.0.0.1 rather
// than "localhost": Node 17+ resolves localhost to IPv6 first, while uvicorn listens
// on IPv4, which shows up as a confusing ECONNREFUSED.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true, changeOrigin: true },
    },
  },
})
