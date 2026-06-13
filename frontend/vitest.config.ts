import { defineConfig } from 'vitest/config';

export default defineConfig({
  // Use esbuild's automatic JSX runtime so components don't need React in scope.
  esbuild: { jsx: 'automatic', jsxImportSource: 'react' },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
