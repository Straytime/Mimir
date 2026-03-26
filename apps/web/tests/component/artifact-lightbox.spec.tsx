import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { ArtifactLightbox } from "@/features/research/components/artifact-lightbox";
import type { ArtifactSummary } from "@/lib/contracts";
import { renderWithStore } from "@/tests/fixtures/render";

const ARTIFACT: ArtifactSummary = {
  artifact_id: "art_001",
  filename: "chart_market.png",
  mime_type: "image/png",
  url: "/api/v1/tasks/tsk_stage0/artifacts/art_001?access_token=abc",
  access_expires_at: "2026-03-27T00:00:00Z",
};

test("renders lightbox with filename and download button", () => {
  renderWithStore(
    <ArtifactLightbox artifact={ARTIFACT} onClose={vi.fn()} />,
  );

  expect(screen.getByText("chart_market.png")).toBeInTheDocument();
  expect(screen.getByText("image/png")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "下载" })).toBeInTheDocument();
});

test("calls onClose when close button is clicked", async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();

  renderWithStore(
    <ArtifactLightbox artifact={ARTIFACT} onClose={onClose} />,
  );

  await user.click(screen.getByRole("button", { name: "关闭" }));

  expect(onClose).toHaveBeenCalledTimes(1);
});

test("calls onClose when Escape key is pressed", async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();

  renderWithStore(
    <ArtifactLightbox artifact={ARTIFACT} onClose={onClose} />,
  );

  await user.keyboard("{Escape}");

  expect(onClose).toHaveBeenCalledTimes(1);
});

test("calls onClose when backdrop is clicked", async () => {
  const user = userEvent.setup();
  const onClose = vi.fn();

  renderWithStore(
    <ArtifactLightbox artifact={ARTIFACT} onClose={onClose} />,
  );

  const backdrop = screen.getByTestId("lightbox-backdrop");
  await user.click(backdrop);

  expect(onClose).toHaveBeenCalledTimes(1);
});
