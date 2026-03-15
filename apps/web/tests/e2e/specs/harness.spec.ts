import { test, expect } from "@playwright/test";

import { MOCK_SERVER_HEALTH_URL } from "../fixtures/constants";

test("loads the Stage 0 shell and reaches the mock server health route", async ({
  page,
  request,
}) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Mimir Frontend Stage 0 Harness" }),
  ).toBeVisible();

  const response = await request.get(MOCK_SERVER_HEALTH_URL);
  expect(response.ok()).toBeTruthy();
  await expect(response.json()).resolves.toEqual({ status: "ok" });
});
