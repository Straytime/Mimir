import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createFetchTaskApiClient } from "@/lib/api/task-api-client";
import { makeCreateTaskResponse } from "@/tests/fixtures/builders";
import {
  normalizeDeliverySummary,
  normalizeTaskUrls,
  resolveApiUrl,
} from "@/lib/api/backend-url";

/**
 * Tests for resolveBaseUrl logic inside createFetchTaskApiClient.
 *
 * The resolve order is:
 *   1. Explicit baseUrl option
 *   2. NEXT_PUBLIC_API_BASE_URL env var
 *   3. window.location.origin (browser)
 *   4. "http://localhost" (server-side fallback)
 */
describe("resolveBaseUrl", () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_BASE_URL;

  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  });

  afterEach(() => {
    if (originalEnv !== undefined) {
      process.env.NEXT_PUBLIC_API_BASE_URL = originalEnv;
    } else {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;
    }
  });

  it("uses explicit baseUrl option when provided", async () => {
    const response = makeCreateTaskResponse();
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const client = createFetchTaskApiClient({
      baseUrl: "http://explicit:9999",
      fetchImpl: mockFetch,
    });

    await client.createTask({ initial_query: "test", config: { clarification_mode: "natural" }, client: { timezone: "UTC", locale: "en" } });

    expect(mockFetch).toHaveBeenCalledWith(
      "http://explicit:9999/api/v1/tasks",
      expect.any(Object),
    );
  });

  it("uses NEXT_PUBLIC_API_BASE_URL env var when no explicit baseUrl", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://env-api:8000";
    const response = makeCreateTaskResponse();

    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const client = createFetchTaskApiClient({ fetchImpl: mockFetch });

    await client.createTask({ initial_query: "test", config: { clarification_mode: "natural" }, client: { timezone: "UTC", locale: "en" } });

    expect(mockFetch).toHaveBeenCalledWith(
      "http://env-api:8000/api/v1/tasks",
      expect.any(Object),
    );
  });

  it("falls back to window.location.origin when env var is not set", async () => {
    const response = makeCreateTaskResponse();
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const client = createFetchTaskApiClient({ fetchImpl: mockFetch });

    await client.createTask({ initial_query: "test", config: { clarification_mode: "natural" }, client: { timezone: "UTC", locale: "en" } });

    // jsdom window.location.origin is "http://localhost"
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/tasks"),
      expect.any(Object),
    );
  });

  it("normalizes task lifecycle URLs against explicit API base url", () => {
    expect(
      normalizeTaskUrls(
        {
          events: "/api/v1/tasks/tsk_1/events",
          heartbeat: "/api/v1/tasks/tsk_1/heartbeat",
          disconnect: "/api/v1/tasks/tsk_1/disconnect",
        },
        "https://api.example.com",
      ),
    ).toEqual({
      events: "https://api.example.com/api/v1/tasks/tsk_1/events",
      heartbeat: "https://api.example.com/api/v1/tasks/tsk_1/heartbeat",
      disconnect: "https://api.example.com/api/v1/tasks/tsk_1/disconnect",
    });
  });

  it("normalizes delivery URLs against explicit API base url", () => {
    expect(
      normalizeDeliverySummary(
        {
          revision_id: "rev_1",
          revision_number: 1,
          word_count: 10,
          artifact_count: 1,
          markdown_zip_url:
            "/api/v1/tasks/tsk_1/downloads/markdown.zip?access_token=zip",
          pdf_url: "/api/v1/tasks/tsk_1/downloads/report.pdf?access_token=pdf",
          artifacts: [
            {
              artifact_id: "art_1",
              filename: "chart.png",
              mime_type: "image/png",
              url: "/api/v1/tasks/tsk_1/artifacts/art_1?access_token=img",
              access_expires_at: "2026-03-16T00:10:00+08:00",
            },
          ],
        },
        "https://api.example.com",
      ),
    ).toMatchObject({
      markdown_zip_url:
        "https://api.example.com/api/v1/tasks/tsk_1/downloads/markdown.zip?access_token=zip",
      pdf_url:
        "https://api.example.com/api/v1/tasks/tsk_1/downloads/report.pdf?access_token=pdf",
      artifacts: [
        {
          url: "https://api.example.com/api/v1/tasks/tsk_1/artifacts/art_1?access_token=img",
        },
      ],
    });
  });

  it("keeps relative URLs when no explicit or env API base exists", () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;

    expect(resolveApiUrl("/api/v1/tasks/tsk_1/events")).toBe(
      "/api/v1/tasks/tsk_1/events",
    );
  });
});
