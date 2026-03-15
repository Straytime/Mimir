import type {
  CreateTaskRequest,
  CreateTaskResponse,
  ErrorResponse,
  ValidationErrorItem,
} from "@/lib/contracts";

export type CreateTaskResult = {
  response: CreateTaskResponse;
  requestId: string | null;
  traceId: string | null;
};

export type TaskApiClient = {
  createTask: (request: CreateTaskRequest) => Promise<CreateTaskResult>;
};

type TaskApiClientErrorArgs = {
  status: number;
  code: string;
  message: string;
  detail: Record<string, unknown>;
  requestId: string | null;
  traceId: string | null;
  retryAfterSeconds: number | null;
};

export class TaskApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly detail: Record<string, unknown>;
  readonly requestId: string | null;
  readonly traceId: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(args: TaskApiClientErrorArgs) {
    super(args.message);
    this.name = "TaskApiClientError";
    this.status = args.status;
    this.code = args.code;
    this.detail = args.detail;
    this.requestId = args.requestId;
    this.traceId = args.traceId;
    this.retryAfterSeconds = args.retryAfterSeconds;
  }
}

type FetchTaskApiClientOptions = {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
};

function resolveBaseUrl(baseUrl: string) {
  if (baseUrl.length > 0) {
    return baseUrl;
  }

  if (typeof window !== "undefined") {
    return window.location.origin;
  }

  return "http://localhost";
}

function parseJsonResponse<T>(value: unknown): T {
  return value as T;
}

function parseRetryAfterSeconds(headerValue: string | null): number | null {
  if (headerValue === null) {
    return null;
  }

  const parsed = Number(headerValue);

  return Number.isFinite(parsed) ? parsed : null;
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return "error" in value;
}

export function isValidationErrorItemArray(
  value: unknown,
): value is ValidationErrorItem[] {
  return Array.isArray(value);
}

export function createFetchTaskApiClient(
  options: FetchTaskApiClientOptions = {},
): TaskApiClient {
  const fetchImpl = options.fetchImpl ?? fetch;
  const baseUrl = resolveBaseUrl(options.baseUrl ?? "");

  return {
    async createTask(request: CreateTaskRequest) {
      const response = await fetchImpl(`${baseUrl}/api/v1/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(request),
      });

      const responseJson = parseJsonResponse<unknown>(await response.json());
      const requestId = response.headers.get("x-request-id");
      const traceIdHeader = response.headers.get("x-trace-id");

      if (!response.ok) {
        const errorResponse = isErrorResponse(responseJson)
          ? responseJson
          : {
              error: {
                code: "unknown",
                message: "请求失败。",
                detail: {},
                request_id: requestId,
                trace_id: traceIdHeader,
              },
            };

        throw new TaskApiClientError({
          status: response.status,
          code: errorResponse.error.code,
          message: errorResponse.error.message,
          detail: errorResponse.error.detail,
          requestId: errorResponse.error.request_id,
          traceId: errorResponse.error.trace_id,
          retryAfterSeconds: parseRetryAfterSeconds(
            response.headers.get("retry-after"),
          ),
        });
      }

      const successResponse = parseJsonResponse<CreateTaskResponse>(responseJson);

      return {
        response: successResponse,
        requestId,
        traceId: traceIdHeader,
      };
    },
  };
}
