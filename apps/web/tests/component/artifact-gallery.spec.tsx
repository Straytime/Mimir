import { screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { expect, test } from "vitest";

import { ArtifactGallery } from "@/features/research/components/artifact-gallery";
import { createResearchSessionStore } from "@/features/research/store/research-session-store";
import {
  makeArtifactSummary,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import { mswServer } from "@/tests/fixtures/msw-server";
import { renderWithStore } from "@/tests/fixtures/render";

function createArtifactStore() {
  return createResearchSessionStore(
    makeResearchSessionState({
      session: {
        taskId: "tsk_stage0",
        taskToken: "secret_stage0",
      },
      remote: {
        snapshot: makeTaskSnapshot({
          phase: "writing_report",
          status: "running",
        }),
      },
    }),
  );
}

test("renders generated artifacts in the gallery after artifact.ready", async () => {
  const artifact = makeArtifactSummary({
    artifact_id: "art_stage0_chart",
    filename: "chart_market_share.png",
    url: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=fresh",
  });
  const store = createArtifactStore();

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      artifacts: [artifact],
    },
  }));

  mswServer.use(
    http.get("*/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart", () => {
      return new HttpResponse(new Uint8Array([137, 80, 78, 71]), {
        status: 200,
        headers: {
          "Content-Type": "image/png",
        },
      });
    }),
  );

  renderWithStore(<ArtifactGallery />, { store });

  expect(await screen.findByAltText("chart_market_share.png")).toBeInTheDocument();
});

test("disables the artifact retry button while delivery refresh is in progress", async () => {
  const artifact = makeArtifactSummary({
    artifact_id: "art_stage0_broken",
    filename: "chart_growth.png",
    url: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_broken?access_token=stale",
  });
  const store = createArtifactStore();

  store.setState((state) => ({
    ...state,
    stream: {
      ...state.stream,
      artifacts: [artifact],
    },
    deliveryUi: {
      ...state.deliveryUi,
      refreshingDelivery: true,
    },
  }));

  mswServer.use(
    http.get("*/api/v1/tasks/tsk_stage0/artifacts/art_stage0_broken", () => {
      return HttpResponse.json(
        {
          error: {
            code: "access_token_invalid",
            message: "链接已失效。",
            detail: {},
            request_id: "req_stage6_artifact",
            trace_id: null,
          },
        },
        { status: 401 },
      );
    }),
  );

  renderWithStore(<ArtifactGallery />, { store });

  expect(await screen.findByRole("button", { name: "重试图片" })).toBeDisabled();
});
