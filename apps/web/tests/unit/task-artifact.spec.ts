import { describe, expect, test } from "vitest";

import {
  findLatestArtifactBySource,
  parseArtifactUrl,
} from "@/features/research/utils/task-artifact";

describe("task artifact url helpers", () => {
  test("parses relative artifact urls against the current browser origin", () => {
    const expectedUrl = new URL(
      "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=stale",
      window.location.origin,
    ).toString();

    expect(
      parseArtifactUrl(
        "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=stale",
      ),
    ).toEqual({
      taskId: "tsk_stage0",
      artifactId: "art_stage0_chart",
      normalizedUrl: expectedUrl,
    });
  });

  test("finds the latest artifact by source when the original markdown image src is relative", () => {
    expect(
      findLatestArtifactBySource({
        taskId: "tsk_stage0",
        src: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=stale",
        streamArtifacts: [],
        deliveryArtifacts: [
          {
            artifact_id: "art_stage0_chart",
            filename: "chart_market_share.png",
            mime_type: "image/png",
            url: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=fresh",
            access_expires_at: "2026-03-16T00:20:00+08:00",
          },
        ],
      }),
    ).toMatchObject({
      artifact_id: "art_stage0_chart",
      url: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=fresh",
    });
  });

  test("finds the latest artifact by source when the markdown image src is canonical", () => {
    expect(
      findLatestArtifactBySource({
        taskId: "tsk_stage0",
        src: "mimir://artifact/art_stage0_chart",
        streamArtifacts: [],
        deliveryArtifacts: [
          {
            artifact_id: "art_stage0_chart",
            filename: "chart_market_share.png",
            mime_type: "image/png",
            url: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=fresh",
            access_expires_at: "2026-03-16T00:20:00+08:00",
          },
        ],
      }),
    ).toMatchObject({
      artifact_id: "art_stage0_chart",
      url: "/api/v1/tasks/tsk_stage0/artifacts/art_stage0_chart?access_token=fresh",
    });
  });
});
