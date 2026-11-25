import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Relative base so the built app works from whatever path `engine serve`
// mounts it at (/board/dist/). The dev server proxies /runs to the engine so
// `npm run dev` reads the same data as the built viewer.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    port: 5173,
    proxy: { '/runs': 'http://localhost:8088' },
  },
})
