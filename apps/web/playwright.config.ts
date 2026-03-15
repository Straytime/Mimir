import { defineConfig, devices } from "@playwright/test";

import {
  MOCK_SERVER_HEALTH_URL,
  WEB_SERVER_ORIGIN,
  WEB_SERVER_PORT,
} from "./tests/e2e/fixtures/constants";

export default defineConfig({
  testDir: "./tests/e2e/specs",
  fullyParallel: false,
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: WEB_SERVER_ORIGIN,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
  webServer: [
    {
      command: `pnpm exec next dev --hostname 127.0.0.1 --port ${WEB_SERVER_PORT}`,
      url: WEB_SERVER_ORIGIN,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "node tests/e2e/fixtures/mock-server.mjs 4100",
      url: MOCK_SERVER_HEALTH_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
