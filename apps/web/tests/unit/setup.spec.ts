import { test, expect } from "vitest";

test("tests/setup registers jest-dom matchers and shared browser mocks", () => {
  document.body.innerHTML = "<div>stage 0</div>";

  expect(document.body).toBeInTheDocument();
  expect(document.body).toHaveTextContent("stage 0");
  expect(window.matchMedia("(min-width: 768px)").matches).toBe(false);
  expect(window.navigator.sendBeacon("/disconnect")).toBe(true);
});
