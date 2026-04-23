import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl  = env.VITE_BACKEND_URL       || 'http://localhost:9000'
  const speedApiUrl = env.VITE_FASTAPI_SPEED_URL  || 'http://localhost:8000'
  const lineApiUrl  = env.VITE_FASTAPI_LINE_URL   || 'http://localhost:8001'

  return {
    plugins: [vue()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true
        },
        '/ai': {
          target: speedApiUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ai/, '')
        },
        '/ai-line': {
          target: lineApiUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ai-line/, '')
        }
      }
    }
  }
})
