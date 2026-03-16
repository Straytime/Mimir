import { describe, expect, test } from "vitest";

import {
  selectCanDownloadMarkdown,
  selectCanDownloadPdf,
  selectCanSubmitClarification,
  selectCanSubmitFeedback,
} from "@/features/research/store/selectors";
import { makeResearchSessionState } from "@/tests/fixtures/builders";

describe("available action selectors", () => {
  test("enable actions when the snapshot exposes the matching available_actions", () => {
    const state = makeResearchSessionState({
      remote: {
        snapshot: {
          ...makeResearchSessionState().remote.snapshot!,
          status: "awaiting_feedback",
          phase: "delivered",
          available_actions: [
            "submit_feedback",
            "download_markdown",
            "download_pdf",
          ],
        },
      },
    });

    expect(selectCanSubmitClarification(state)).toBe(false);
    expect(selectCanSubmitFeedback(state)).toBe(true);
    expect(selectCanDownloadMarkdown(state)).toBe(true);
    expect(selectCanDownloadPdf(state)).toBe(true);
  });

  test("disable actions when the task is terminal even if available_actions is stale", () => {
    const state = makeResearchSessionState({
      remote: {
        snapshot: {
          ...makeResearchSessionState().remote.snapshot!,
          status: "failed",
          available_actions: [
            "submit_clarification",
            "submit_feedback",
            "download_markdown",
            "download_pdf",
          ],
        },
      },
      ui: {
        terminalReason: "failed",
      },
    });

    expect(selectCanSubmitClarification(state)).toBe(false);
    expect(selectCanSubmitFeedback(state)).toBe(false);
    expect(selectCanDownloadMarkdown(state)).toBe(false);
    expect(selectCanDownloadPdf(state)).toBe(false);
  });

  test("disable feedback and downloads while waiting for the next revision", () => {
    const state = makeResearchSessionState({
      remote: {
        snapshot: {
          ...makeResearchSessionState().remote.snapshot!,
          status: "awaiting_feedback",
          phase: "delivered",
          available_actions: [
            "submit_feedback",
            "download_markdown",
            "download_pdf",
          ],
        },
      },
      ui: {
        revisionTransition: {
          status: "waiting_next_revision",
          pendingRevisionId: "rev_stage1",
          pendingRevisionNumber: 2,
        },
      },
    });

    expect(selectCanSubmitFeedback(state)).toBe(false);
    expect(selectCanDownloadMarkdown(state)).toBe(false);
    expect(selectCanDownloadPdf(state)).toBe(false);
  });
});
