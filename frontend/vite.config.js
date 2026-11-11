import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/dashboard': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/project': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/api': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/predict': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/result': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:5000', changeOrigin: true }
    }
  }
})
