import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.ts'],
    exclude: ['node_modules', 'dist'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'markdown'],
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.d.ts', 'src/server/index.ts', 'src/database/*.sql'],
      threshold: {
        lines: 80,
        functions: 80,
        branches: 70,
        statements: 80
      },
      reportsDirectory: './tests/coverage'
    },
    reporters: ['verbose', 'junit'],
    outputFile: {
      junit: './tests/report/junit-results.xml'
    },
    testTimeout: 30000,
    hookTimeout: 30000
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
});
