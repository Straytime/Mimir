import { test, expect } from "@playwright/test";

import { MOCK_SERVER_HEALTH_URL } from "../fixtures/constants";

test("loads the research workspace shell and reaches the mock server health route", async ({
  page,
  request,
}) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "AI 研究工作台" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "从空态进入研究工作台" }),
  ).toBeVisible();

  const response = await request.get(MOCK_SERVER_HEALTH_URL);
  expect(response.ok()).toBeTruthy();
  await expect(response.json()).resolves.toEqual({ status: "ok" });
});
