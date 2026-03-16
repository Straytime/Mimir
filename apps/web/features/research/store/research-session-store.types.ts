import type {
  ArtifactSummary,
  ClarificationMode,
  ClarificationQuestionSet,
  CreateTaskResponse,
  DeliverySummary,
  EventEnvelope,
  RevisionSummary,
  TaskDetailResponse,
  TaskSnapshot,
} from "@/lib/contracts";

export type SseState = "idle" | "connecting" | "open" | "closed" | "failed";

export type PendingAction =
  | "creating_task"
  | "submitting_clarification"
  | "submitting_feedback"
  | "disconnecting"
  | null;

export type RevisionTransitionState = {
  status: "idle" | "waiting_next_revision" | "switching";
  pendingRevisionId: string | null;
  pendingRevisionNumber: number | null;
};

export type TerminalReason = "terminated" | "failed" | "expired" | null;

export type CreateTaskErrorCode =
  | "validation_error"
  | "resource_busy"
  | "ip_quota_exceeded"
  | "unknown"
  | null;

export type CreateTaskUiState = {
  clarificationModeDraft: ClarificationMode;
  initialQueryError: string | null;
  submitError: string | null;
  errorCode: CreateTaskErrorCode;
  nextAvailableAt: string | null;
  retryAfterLabel: string | null;
};

export type ResearchOutlineSection = {
  section_id: string;
  title: string;
  description: string;
  order: number;
};

export type ResearchOutline = {
  title: string;
  sections: ResearchOutlineSection[];
  entities: string[];
};

export type TimelineItem = {
  id: string;
  revisionId: string | null;
  kind: "phase" | "reasoning" | "collect" | "summary" | "tool_call" | "system";
  label: string;
  detail?: string;
  status: "running" | "completed" | "failed";
  occurredAt: string;
  subtaskId?: string;
  toolCallId?: string;
  collectTarget?: string;
};

export type ResearchSessionState = {
  session: {
    taskId: string | null;
    taskToken: string | null;
    traceId: string | null;
    requestId: string | null;
    eventsUrl: string | null;
    heartbeatUrl: string | null;
    disconnectUrl: string | null;
    connectDeadlineAt: string | null;
    sseState: SseState;
    lastHeartbeatAt: string | null;
  };
  remote: {
    snapshot: TaskSnapshot | null;
    currentRevision: RevisionSummary | null;
    delivery: DeliverySummary | null;
  };
  stream: {
    analysisText: string;
    clarificationText: string;
    questionSet: ClarificationQuestionSet | null;
    reportMarkdown: string;
    outline: ResearchOutline | null;
    outlineReady: boolean;
    timeline: TimelineItem[];
    artifacts: ArtifactSummary[];
    lastEventSeq: number | null;
  };
  ui: {
    initialPromptDraft: string;
    clarificationDraft: string;
    feedbackDraft: string;
    createTask: CreateTaskUiState;
    optionAnswers: Record<string, string>;
    clarificationCountdownDeadlineAt: string | null;
    clarificationCountdownDurationSeconds: number | null;
    clarificationFieldError: string | null;
    clarificationSubmitError: string | null;
    pendingAction: PendingAction;
    revisionTransition: RevisionTransitionState;
    reportAutoScrollEnabled: boolean;
    terminalReason: TerminalReason;
  };
  deliveryUi: {
    refreshingDelivery: boolean;
    markdownDownloadState: "idle" | "loading" | "error";
    pdfDownloadState: "idle" | "loading" | "error";
  };
};

export type ResearchSessionStoreActions = {
  reset: () => void;
  setInitialPromptDraft: (draft: string) => void;
  setCreateTaskClarificationModeDraft: (mode: ClarificationMode) => void;
  setCreateTaskUiState: (patch: Partial<CreateTaskUiState>) => void;
  clearCreateTaskUiState: () => void;
  setPendingAction: (pendingAction: PendingAction) => void;
  setClarificationDraft: (draft: string) => void;
  setClarificationFieldError: (message: string | null) => void;
  setClarificationSubmitError: (message: string | null) => void;
  clearClarificationUiState: () => void;
  setOptionAnswer: (args: {
    questionId: string;
    optionId: string;
  }) => void;
  setClarificationCountdown: (args: {
    durationSeconds: number;
    startedAt?: string | null;
  }) => void;
  clearClarificationCountdown: () => void;
  mergeRemoteSnapshot: (snapshot: TaskSnapshot) => void;
  setSessionContext: (
    sessionPatch: Partial<ResearchSessionState["session"]>,
  ) => void;
  setTerminalState: (args: {
    terminalReason: Exclude<TerminalReason, null>;
    timestamp: string;
    expiresAt?: string | null;
    sseState?: SseState;
  }) => void;
  bootstrapCreateTask: (args: {
    response: CreateTaskResponse;
    requestId: string | null;
  }) => void;
  mergeTaskDetail: (detail: TaskDetailResponse) => void;
  applyEvent: (event: EventEnvelope) => void;
};

export type ResearchSessionStore = ResearchSessionState &
  ResearchSessionStoreActions;

export function createResearchSessionState(): ResearchSessionState {
  return {
    session: {
      taskId: null,
      taskToken: null,
      traceId: null,
      requestId: null,
      eventsUrl: null,
      heartbeatUrl: null,
      disconnectUrl: null,
      connectDeadlineAt: null,
      sseState: "idle",
      lastHeartbeatAt: null,
    },
    remote: {
      snapshot: null,
      currentRevision: null,
      delivery: null,
    },
    stream: {
      analysisText: "",
      clarificationText: "",
      questionSet: null,
      reportMarkdown: "",
      outline: null,
      outlineReady: false,
      timeline: [],
      artifacts: [],
      lastEventSeq: null,
    },
    ui: {
      initialPromptDraft: "",
      clarificationDraft: "",
      feedbackDraft: "",
      createTask: {
        clarificationModeDraft: "natural",
        initialQueryError: null,
        submitError: null,
        errorCode: null,
        nextAvailableAt: null,
        retryAfterLabel: null,
      },
      optionAnswers: {},
      clarificationCountdownDeadlineAt: null,
      clarificationCountdownDurationSeconds: null,
      clarificationFieldError: null,
      clarificationSubmitError: null,
      pendingAction: null,
      revisionTransition: {
        status: "idle",
        pendingRevisionId: null,
        pendingRevisionNumber: null,
      },
      reportAutoScrollEnabled: true,
      terminalReason: null,
    },
    deliveryUi: {
      refreshingDelivery: false,
      markdownDownloadState: "idle",
      pdfDownloadState: "idle",
    },
  };
}
