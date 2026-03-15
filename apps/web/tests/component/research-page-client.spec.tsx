import { screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { ResearchPageClient } from "@/features/research/components/research-page-client";
import { renderWithStore } from "@/tests/fixtures/render";

test("renders the minimal Stage 0 client shell", () => {
  renderWithStore(<ResearchPageClient />);

  expect(
    screen.getByRole("heading", { name: "Mimir Frontend Stage 0 Harness" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/without entering the research workflow implementation/i),
  ).toBeInTheDocument();
});
