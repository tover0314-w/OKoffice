import { resolve } from 'path';
import react from '@vitejs/plugin-react';
import { defineConfig, externalizeDepsPlugin } from 'electron-vite';

const shellRoot = __dirname;
const mainRoot = resolve(shellRoot, 'src/main');
const rendererRoot = resolve(shellRoot, 'src/renderer');

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    resolve: {
      alias: {
        '@main': mainRoot,
        '@shared': resolve(shellRoot, 'src/shared'),
      },
      extensions: ['.ts', '.js'],
    },
    build: {
      outDir: resolve(shellRoot, 'dist/main'),
      rollupOptions: {
        input: resolve(mainRoot, 'index.ts'),
      },
    },
  },

  preload: {
    plugins: [externalizeDepsPlugin()],
    resolve: {
      alias: {
        '@shared': resolve(shellRoot, 'src/shared'),
      },
    },
    build: {
      outDir: resolve(shellRoot, 'dist/preload'),
      rollupOptions: {
        input: resolve(shellRoot, 'src/preload/index.ts'),
      },
    },
  },

  renderer: {
    root: rendererRoot,
    plugins: [react()],
    resolve: {
      alias: {
        '@': rendererRoot,
        '@shared': resolve(shellRoot, 'src/shared'),
      },
      extensions: ['.ts', '.tsx', '.js', '.jsx', '.css'],
    },
    build: {
      outDir: resolve(shellRoot, 'dist/renderer'),
      target: 'es2022',
      rollupOptions: {
        input: resolve(rendererRoot, 'index.html'),
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-arco': ['@arco-design/web-react'],
            'vendor-pdf': ['pdfjs-dist', 'react-pdf'],
            'vendor-flow': ['@xyflow/react'],
            'vendor-markdown': ['react-markdown', 'react-syntax-highlighter'],
          },
        },
      },
    },
    optimizeDeps: {
      exclude: ['electron'],
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@arco-design/web-react',
        'classnames',
        'eventemitter3',
      ],
    },
  },
});
