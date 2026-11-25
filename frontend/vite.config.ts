import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import path from 'node:path'

const src = (p: string) => path.resolve(import.meta.dirname, 'src', p)
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@app': src('app'), '@shared': src('shared'), '@features': src('features') } },
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
