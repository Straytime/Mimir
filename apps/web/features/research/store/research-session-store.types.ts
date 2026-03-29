import type {
  ArtifactSummary,
  ClarificationMode,
  ClarificationQuestionSet,
  CreateTaskResponse,
  DeliverySummary,
  EventEnvelope,
  ResearchOutline,
  RevisionSummary,
  TaskDetailResponse,
  TaskSnapshot,
  TerminationReason,
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
    explicitAbortRequested: boolean;
    lastHeartbeatAt: string | null;
    lastServerActivityAt: string | null;
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
    feedbackFieldError: string | null;
    feedbackSubmitError: string | null;
    pendingAction: PendingAction;
    revisionTransition: RevisionTransitionState;
    reportAutoScrollEnabled: boolean;
    terminalReason: TerminalReason;
    terminationDetail: TerminationReason | null;
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
  setFeedbackDraft: (draft: string) => void;
  setFeedbackFieldError: (message: string | null) => void;
  setFeedbackSubmitError: (message: string | null) => void;
  clearFeedbackUiState: () => void;
  startRevisionTransition: (args: {
    pendingRevisionId: string;
    pendingRevisionNumber: number;
  }) => void;
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
  setReportAutoScrollEnabled: (enabled: boolean) => void;
  setRefreshingDelivery: (refreshingDelivery: boolean) => void;
  setDownloadState: (args: {
    format: "markdown" | "pdf";
    state: ResearchSessionState["deliveryUi"]["markdownDownloadState"];
  }) => void;
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
      explicitAbortRequested: false,
      lastHeartbeatAt: null,
      lastServerActivityAt: null,
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
      feedbackFieldError: null,
      feedbackSubmitError: null,
      pendingAction: null,
      revisionTransition: {
        status: "idle",
        pendingRevisionId: null,
        pendingRevisionNumber: null,
      },
      reportAutoScrollEnabled: true,
      terminalReason: null,
      terminationDetail: null,
    },
    deliveryUi: {
      refreshingDelivery: false,
      markdownDownloadState: "idle",
      pdfDownloadState: "idle",
    },
  };
}
