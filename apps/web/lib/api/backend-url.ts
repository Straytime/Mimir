import type {
  ArtifactSummary,
  DeliverySummary,
  TaskUrls,
} from "@/lib/contracts";

const FALLBACK_BASE_URL = "http://localhost";

export function resolveApiBaseUrl(explicitBaseUrl = "") {
  if (explicitBaseUrl.length > 0) {
    return explicitBaseUrl;
  }

  const envBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  if (envBaseUrl.length > 0) {
    return envBaseUrl;
  }

  if (typeof window !== "undefined") {
    return window.location.origin;
  }

  return FALLBACK_BASE_URL;
}

function shouldNormalizeWithApiBase(explicitBaseUrl = "") {
  return explicitBaseUrl.length > 0 || (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").length > 0;
}

export function resolveApiUrl(url: string, explicitBaseUrl = "") {
  if (!shouldNormalizeWithApiBase(explicitBaseUrl)) {
    return url;
  }

  return new URL(url, resolveApiBaseUrl(explicitBaseUrl)).toString();
}

export function normalizeTaskUrls(urls: TaskUrls, explicitBaseUrl = ""): TaskUrls {
  return {
    events: resolveApiUrl(urls.events, explicitBaseUrl),
    heartbeat: resolveApiUrl(urls.heartbeat, explicitBaseUrl),
    disconnect: resolveApiUrl(urls.disconnect, explicitBaseUrl),
  };
}

export function normalizeArtifactSummary(
  artifact: ArtifactSummary,
  explicitBaseUrl = "",
): ArtifactSummary {
  return {
    ...artifact,
    url: resolveApiUrl(artifact.url, explicitBaseUrl),
  };
}

export function normalizeDeliverySummary(
  delivery: DeliverySummary,
  explicitBaseUrl = "",
): DeliverySummary {
  return {
    ...delivery,
    markdown_zip_url: resolveApiUrl(delivery.markdown_zip_url, explicitBaseUrl),
    pdf_url: resolveApiUrl(delivery.pdf_url, explicitBaseUrl),
    artifacts: delivery.artifacts.map((artifact) =>
      normalizeArtifactSummary(artifact, explicitBaseUrl),
    ),
  };
}
