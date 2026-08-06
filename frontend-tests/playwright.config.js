import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 15000,
  use: {
    baseURL: 'http://127.0.0.1:8080',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'PYTHONPATH=src .venv/bin/uvicorn main:app --port 8080 --host 127.0.0.1',
    url: 'http://127.0.0.1:8080/health',
    cwd: '..',
    reuseExistingServer: true,
    timeout: 15000,
  },
});
