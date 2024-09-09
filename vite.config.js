import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  base: 'typing/bigram-comfort-study/',  
  resolve: {
    alias: {
      'jspsych': path.resolve(__dirname, 'node_modules/jspsych'),
      '@jspsych': path.resolve(__dirname, 'node_modules/@jspsych'),
    },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main: 'index.html',
      },
    },
  },
  optimizeDeps: {
    include: ['jspsych']
  },
});
