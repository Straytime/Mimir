import { expect, test } from "vitest";

import { selectCollectProgress } from "@/features/research/store/selectors";
import {
  makeCollectionCollectGroup,
  makeCollectionPlanRoundNode,
  makeCollectionTraceRoot,
  makeResearchSessionState,
  makeTaskSnapshot,
} from "@/tests/fixtures/builders";

test("returns progress when phase is collecting with mixed statuses", () => {
  const state = makeResearchSessionState({
    remote: {
      snapshot: makeTaskSnapshot({
        phase: "collecting",
        status: "running",
      }),
    },
    stream: {
      collectionTrace: makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                id: "c1",
                collect: {
                  id: "collect_1",
                  kind: "collect",
                  label: "搜集子任务 1",
                  status: "completed",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
              makeCollectionCollectGroup({
                id: "c2",
                collect: {
                  id: "collect_2",
                  kind: "collect",
                  label: "搜集子任务 2",
                  status: "running",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
              makeCollectionCollectGroup({
                id: "c3",
                collect: {
                  id: "collect_3",
                  kind: "collect",
                  label: "搜集子任务 3",
                  status: "running",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
            ],
          }),
        ],
      }),
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
      collectionTrace: makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                id: "c1",
                collect: {
                  id: "collect_1",
                  kind: "collect",
                  label: "搜集子任务 1",
                  status: "completed",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
              makeCollectionCollectGroup({
                id: "c2",
                collect: {
                  id: "collect_2",
                  kind: "collect",
                  label: "搜集子任务 2",
                  status: "completed",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
            ],
          }),
        ],
      }),
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
      collectionTrace: makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                id: "c1",
                collect: {
                  id: "collect_1",
                  kind: "collect",
                  label: "搜集子任务 1",
                  status: "completed",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
            ],
          }),
        ],
      }),
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
      collectionTrace: {
        nodes: [],
      },
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
      collectionTrace: makeCollectionTraceRoot({
        nodes: [
          makeCollectionPlanRoundNode({
            collectGroups: [
              makeCollectionCollectGroup({
                id: "c1",
                collect: {
                  id: "collect_1",
                  kind: "collect",
                  label: "搜集子任务 1",
                  status: "completed",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
              makeCollectionCollectGroup({
                id: "c2",
                collect: {
                  id: "collect_2",
                  kind: "collect",
                  label: "搜集子任务 2",
                  status: "failed",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
              makeCollectionCollectGroup({
                id: "c3",
                collect: {
                  id: "collect_3",
                  kind: "collect",
                  label: "搜集子任务 3",
                  status: "running",
                  occurredAt: "2026-03-27T00:00:00Z",
                  entries: [],
                },
              }),
            ],
          }),
        ],
      }),
    },
  });

  expect(selectCollectProgress(state)).toEqual({ total: 3, finished: 2 });
});
