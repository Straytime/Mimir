import { describe, expect, test } from "vitest";

import { reduceResearchSessionEvent } from "@/features/research/reducers/event-reducer";
import { makeResearchSessionState } from "@/tests/fixtures/builders";
import {
  makeAnalysisCompletedEvent,
  makeAnalysisDeltaEvent,
  makeArtifactReadyEvent,
  makeClarificationDeltaEvent,
  makeClarificationFallbackToNaturalEvent,
  makeClarificationNaturalReadyEvent,
  makeClarificationOptionsReadyEvent,
  makeClarificationCountdownStartedEvent,
  makeHeartbeatEvent,
  makeOutlineCompletedEvent,
  makePhaseChangedEvent,
  makeReportCompletedEvent,
  makeTaskAwaitingFeedbackEvent,
  makeTaskCreatedEvent,
  makeTaskExpiredEvent,
  makeTaskFailedEvent,
  makeTaskTerminatedEvent,
  makeWriterDeltaEvent,
} from "@/tests/fixtures/builders";

describe("reduceResearchSessionEvent", () => {
  test("handles task.created by replacing the snapshot from the authoritative event", () => {
    const state = makeResearchSessionState({
      remote: {
        snapshot: null,
      },
    });
    const event = makeTaskCreatedEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.remote.snapshot).toEqual(event.payload.snapshot);
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles phase.changed by updating phase and status", () => {
    const state = makeResearchSessionState();
    const event = makePhaseChangedEvent({
      revision_id: "rev_stage1",
      payload: {
        from_phase: "clarifying",
        to_phase: "analyzing_requirement",
        status: "running",
      },
      timestamp: "2026-03-13T14:31:11+08:00",
    });

    const result = reduceResearchSessionEvent(state, event);

    expect(result.remote.snapshot).toMatchObject({
      phase: "analyzing_requirement",
      status: "running",
      active_revision_id: "rev_stage1",
      updated_at: "2026-03-13T14:31:11+08:00",
    });
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles heartbeat by recording the last heartbeat time", () => {
    const state = makeResearchSessionState();
    const event = makeHeartbeatEvent({
      payload: {
        server_time: "2026-03-13T14:35:30+08:00",
      },
    });

    const result = reduceResearchSessionEvent(state, event);

    expect(result.session.lastHeartbeatAt).toBe("2026-03-13T14:35:30+08:00");
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles clarification.delta by appending streamed clarification text", () => {
    const state = makeResearchSessionState({
      stream: {
        clarificationText: "已有前文。",
      },
    });
    const event = makeClarificationDeltaEvent({
      payload: {
        delta: "继续追问。",
      },
    });

    const result = reduceResearchSessionEvent(state, event);

    expect(result.stream.clarificationText).toBe("已有前文。继续追问。");
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles clarification.natural.ready by enabling clarification submission in natural mode", () => {
    const state = makeResearchSessionState();
    const event = makeClarificationNaturalReadyEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.remote.snapshot).toMatchObject({
      status: "awaiting_user_input",
      available_actions: ["submit_clarification"],
    });
    expect(result.stream.questionSet).toBeNull();
    expect(result.ui.optionAnswers).toEqual({});
  });

  test("handles clarification.options.ready by storing question_set and defaulting every answer to o_auto", () => {
    const state = makeResearchSessionState();
    const event = makeClarificationOptionsReadyEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.stream.questionSet).toEqual(event.payload.question_set);
    expect(result.ui.optionAnswers).toEqual({
      q_1: "o_auto",
    });
    expect(result.remote.snapshot).toMatchObject({
      status: "awaiting_user_input",
      available_actions: ["submit_clarification"],
    });
  });

  test("handles clarification.countdown.started by storing a client-side deadline", () => {
    const state = makeResearchSessionState();
    const event = makeClarificationCountdownStartedEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.ui.clarificationCountdownDeadlineAt).toBe(
      "2026-03-13T06:30:51.000Z",
    );
  });

  test("handles clarification.fallback_to_natural by clearing options state", () => {
    const state = makeResearchSessionState({
      stream: {
        questionSet: makeClarificationOptionsReadyEvent().payload.question_set,
      },
      ui: {
        optionAnswers: {
          q_1: "o_1",
        },
        clarificationCountdownDeadlineAt: "2026-03-13T14:30:51.000Z",
      },
    });
    const event = makeClarificationFallbackToNaturalEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.stream.questionSet).toBeNull();
    expect(result.ui.optionAnswers).toEqual({});
    expect(result.ui.clarificationCountdownDeadlineAt).toBeNull();
  });

  test("handles analysis.delta by appending analysis text", () => {
    const state = makeResearchSessionState({
      stream: {
        analysisText: "已有分析：",
      },
    });
    const event = makeAnalysisDeltaEvent({
      payload: {
        delta: "继续补全需求结构。",
      },
    });

    const result = reduceResearchSessionEvent(state, event);

    expect(result.stream.analysisText).toBe("已有分析：继续补全需求结构。");
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles analysis.completed by storing requirement_detail and clearing analysis text", () => {
    const state = makeResearchSessionState({
      stream: {
        analysisText: "正在分析中",
      },
      remote: {
        currentRevision: null,
      },
    });
    const event = makeAnalysisCompletedEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.stream.analysisText).toBe("");
    expect(result.remote.currentRevision).toMatchObject({
      revision_id: "rev_stage0",
      revision_number: 1,
      requirement_detail: event.payload.requirement_detail,
    });
  });

  test("handles outline.completed by storing the outline and marking it as ready", () => {
    const state = makeResearchSessionState({
      stream: {
        outline: null,
        outlineReady: false,
      },
    });
    const event = makeOutlineCompletedEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.stream.outline).toEqual(event.payload.outline);
    expect(result.stream.outlineReady).toBe(true);
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles writer.delta by appending report markdown", () => {
    const state = makeResearchSessionState({
      stream: {
        reportMarkdown: "# 已有标题\n",
      },
    });
    const event = makeWriterDeltaEvent({
      payload: {
        delta: "\n追加正文段落。",
      },
    });

    const result = reduceResearchSessionEvent(state, event);

    expect(result.stream.reportMarkdown).toBe("# 已有标题\n\n追加正文段落。");
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles artifact.ready by appending artifacts into the stream", () => {
    const existingArtifact = makeArtifactReadyEvent().payload.artifact;
    const state = makeResearchSessionState({
      stream: {
        artifacts: [existingArtifact],
      },
    });
    const event = makeArtifactReadyEvent({
      payload: {
        artifact: {
          ...existingArtifact,
          artifact_id: "art_stage0_new",
          filename: "chart_growth.png",
        },
      },
    });

    const result = reduceResearchSessionEvent(state, event);

    expect(result.stream.artifacts).toEqual([
      existingArtifact,
      event.payload.artifact,
    ]);
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles report.completed by updating the current delivery payload", () => {
    const state = makeResearchSessionState({
      remote: {
        delivery: null,
      },
    });
    const event = makeReportCompletedEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.remote.delivery).toEqual(event.payload.delivery);
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test("handles task.awaiting_feedback by updating expires_at and delivery actions", () => {
    const state = makeResearchSessionState({
      remote: {
        snapshot: makeResearchSessionState().remote.snapshot,
      },
    });
    const event = makeTaskAwaitingFeedbackEvent();

    const result = reduceResearchSessionEvent(state, event);

    expect(result.remote.snapshot).toMatchObject({
      status: "awaiting_feedback",
      phase: "delivered",
      expires_at: event.payload.expires_at,
      available_actions: event.payload.available_actions,
      updated_at: event.timestamp,
    });
    expect(result.stream.lastEventSeq).toBe(event.seq);
  });

  test.each([
    {
      name: "task.failed",
      event: makeTaskFailedEvent(),
      terminalReason: "failed",
      status: "failed",
      expiresAt: null,
    },
    {
      name: "task.terminated",
      event: makeTaskTerminatedEvent(),
      terminalReason: "terminated",
      status: "terminated",
      expiresAt: null,
    },
    {
      name: "task.expired",
      event: makeTaskExpiredEvent(),
      terminalReason: "expired",
      status: "expired",
      expiresAt: "2026-03-13T15:25:00+08:00",
    },
  ])(
    "handles $name by switching the store into a terminal state",
    ({ event, terminalReason, status, expiresAt }) => {
      const state = makeResearchSessionState({
        remote: {
          snapshot: {
            ...makeResearchSessionState().remote.snapshot!,
            available_actions: ["submit_feedback", "download_markdown", "download_pdf"],
          },
        },
      });

      const result = reduceResearchSessionEvent(state, event);

      expect(result.ui.terminalReason).toBe(terminalReason);
      expect(result.remote.snapshot).toMatchObject({
        status,
        available_actions: [],
      });
      expect(result.remote.snapshot?.expires_at ?? null).toBe(expiresAt);
      expect(result.stream.lastEventSeq).toBe(event.seq);
    },
  );

  test("keeps unsupported events as a no-op for the current stage", () => {
    const state = makeResearchSessionState();
    const event = {
      ...makeClarificationDeltaEvent(),
      event: "feedback.submitted",
    } as unknown as Parameters<typeof reduceResearchSessionEvent>[1];

    const result = reduceResearchSessionEvent(state, event);

    expect(result).toBe(state);
  });
});
