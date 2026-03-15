import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ResearchConfigPanel } from "@/features/research/components/research-config-panel";
import { renderWithStore } from "@/tests/fixtures/render";

test("ResearchConfigPanel defaults to natural clarification mode", () => {
  renderWithStore(<ResearchConfigPanel />);

  expect(screen.getByRole("radio", { name: /自然澄清/i })).toBeChecked();
  expect(screen.getByRole("radio", { name: /选单澄清/i })).not.toBeChecked();
});
