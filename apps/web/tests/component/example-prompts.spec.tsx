import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import { ExamplePrompts } from "@/features/research/components/example-prompts";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import { renderWithStore } from "@/tests/fixtures/render";

test("renders example prompt cards", () => {
  renderWithStore(<ExamplePrompts />);

  const buttons = screen.getAllByRole("button");
  expect(buttons.length).toBeGreaterThanOrEqual(2);
  expect(buttons.length).toBeLessThanOrEqual(3);
});

test("clicking an example card fills the initialPromptDraft in store", async () => {
  const user = userEvent.setup();
  const store = createResearchSessionStore();

  renderWithStore(<ExamplePrompts />, { store });

  const firstCard = screen.getAllByRole("button")[0]!;
  const cardText = firstCard.textContent!;

  await user.click(firstCard);

  expect(store.getState().ui.initialPromptDraft).toBe(cardText);
});
