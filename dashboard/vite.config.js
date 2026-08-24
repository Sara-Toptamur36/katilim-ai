import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
//
// base yalnizca `command === 'build'` iken '/katilim-ai/' olur - GitHub
// Pages repo adini yol onekine ekliyor (https://<kullanici>.github.io/
// katilim-ai/). `npm run dev` (yerel gelistirme, komut='serve') '/' olarak
// KALIR - Vite'in base'i varsayilan olarak dev sunucusuna da uyguladigi
// icin bunu SART kosmak gerekti, aksi halde herkesin
// localhost:5173/katilim-ai/ acmasi gerekirdi (olculmedi, bilinen Vite
// davranisi - https://vite.dev/config/shared-options.html#base).
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/katilim-ai/' : '/',
  build: {
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('antd') || id.includes('@ant-design')) {
              return 'antd';
            }
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'vendor';
            }
          }
        },
      },
    },
  },
}))
