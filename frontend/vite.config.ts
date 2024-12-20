import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { loadEnv } from 'vite'
import type { Plugin } from 'vite'
import fs from 'fs'

// Plugin to generate manifest file
function generateManifest(): Plugin {
  return {
    name: 'generate-manifest',
    writeBundle() {
      const manifestContent = {
        url: process.env.VITE_FRONTEND_URL,
        name: "TETRIX",
        iconUrl: `${process.env.VITE_FRONTEND_URL}/tetrix-icon.png`,
        termsOfUseUrl: `${process.env.VITE_FRONTEND_URL}/terms.html`,
        privacyPolicyUrl: `${process.env.VITE_FRONTEND_URL}/privacy.html`
      };

      // Write manifest file to dist root
      fs.writeFileSync(
        'dist/tonconnect-manifest.json',
        JSON.stringify(manifestContent, null, 2)
      );
    }
  }
}

export default defineConfig(({ mode }) => {
  // Load env file from project root
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [
      react(),
      generateManifest()
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    define: {
      // Ensure these values are available in production
      'process.env.NODE_ENV': JSON.stringify(mode),
      'process.env.VITE_APP_URL': JSON.stringify(env.VITE_APP_URL),
      'global': 'globalThis',
    },
    build: {
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks: {
            'ton-connect': ['@tonconnect/sdk', '@tonconnect/ui', '@tonconnect/ui-react'],
          }
        }
      }
    },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:5000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    }
  }
}) 