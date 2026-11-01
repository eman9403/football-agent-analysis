import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'SCOUTING_')
  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': env.SCOUTING_API_PROXY_URL ?? 'http://127.0.0.1:8000',
      },
    },
  }
})
