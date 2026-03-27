import { expect, test } from "vitest";

import { selectCollectProgress } from "@/features/research/store/selectors";
import {
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";
import type { TimelineItem } from "@/features/research/store/research-session-store.types";

function makeCollectItem(
  overrides: Partial<TimelineItem> & { id: string },
): TimelineItem {
  return {
    revisionId: "rev_0",
    kind: "collect",
    label: "搜集子任务",
    status: "running",
    occurredAt: "2026-03-27T00:00:00Z",
    ...overrides,
  };
}

test("returns progress when phase is collecting with mixed statuses", () => {
  const state = makeResearchSessionState({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "collecting",
        status: "running",
      }),
    },
    stream: {
      timeline: [
        makeCollectItem({ id: "c1", status: "completed" }),
        makeCollectItem({ id: "c2", status: "running" }),
        makeCollectItem({ id: "c3", status: "running" }),
      ],
    },
  });

  expect(selectCollectProgress(state)).toEqual({ total: 3, finished: 1 });
});

test("returns progress when phase is summarizing_collection", () => {
  const state = makeResearchSessionState({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "summarizing_collection",
        status: "running",
      }),
    },
    stream: {
      timeline: [
        makeCollectItem({ id: "c1", status: "completed" }),
        makeCollectItem({ id: "c2", status: "completed" }),
      ],
    },
  });

  expect(selectCollectProgress(state)).toEqual({ total: 2, finished: 2 });
});

test("returns null when phase is not collecting or summarizing", () => {
  const state = makeResearchSessionState({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "writing_report",
        status: "running",
      }),
    },
    stream: {
      timeline: [
        makeCollectItem({ id: "c1", status: "completed" }),
      ],
    },
  });

  expect(selectCollectProgress(state)).toBeNull();
});

test("returns zero totals when no collect items exist", () => {
  const state = makeResearchSessionState({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "collecting",
        status: "running",
      }),
    },
    stream: {
      timeline: [],
    },
  });

  expect(selectCollectProgress(state)).toEqual({ total: 0, finished: 0 });
});

test("counts failed collect items as finished", () => {
  const state = makeResearchSessionState({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "collecting",
        status: "running",
      }),
    },
    stream: {
      timeline: [
        makeCollectItem({ id: "c1", status: "completed" }),
        makeCollectItem({ id: "c2", status: "failed" }),
        makeCollectItem({ id: "c3", status: "running" }),
      ],
    },
  });

  expect(selectCollectProgress(state)).toEqual({ total: 3, finished: 2 });
});
