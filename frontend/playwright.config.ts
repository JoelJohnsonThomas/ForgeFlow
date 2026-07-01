import { defineConfig, devices } from '@playwright/test'

// Serve the built SPA on this port for e2e; the webServer block below starts it.
const PORT = 4173
const BASE_URL = `http://localhost:${PORT}`

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Keep the built-in 'list' reporter and add TestRelic analytics alongside it.
  // TestRelic reads TESTRELIC_API_KEY from the environment to upload the timeline.
  reporter: [
    ['list'],
    ['@testrelic/playwright-analytics', {
      outputPath: './test-results/analytics-timeline.json',
      includeStackTrace: false,
      includeCodeSnippets: false,
      includeNetworkStats: true,
    }],
  ],

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  // Build + serve the SPA so `npx playwright test` is self-contained. Locally we
  // reuse an already-running preview; CI always starts a fresh one.
  webServer: {
    command: 'npm run build && npm run preview -- --port 4173 --strictPort',
    url: BASE_URL,
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
  },
}