import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

import { installBrowserMocks } from "./fixtures/browser";

installBrowserMocks();

afterEach(() => {
  cleanup();
});
