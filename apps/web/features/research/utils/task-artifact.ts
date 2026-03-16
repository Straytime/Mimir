"use client";

import type { ArtifactSummary } from "@/lib/contracts";

type ArtifactUrlMatch = {
  taskId: string;
  artifactId: string;
  normalizedUrl: string;
};

const FALLBACK_BASE_URL = "http://localhost";

function resolveUrl(url: string) {
  return new URL(
    url,
    typeof window === "undefined" ? FALLBACK_BASE_URL : window.location.origin,
  );
}

export function parseArtifactUrl(url: string): ArtifactUrlMatch | null {
  try {
    const resolvedUrl = resolveUrl(url);
    const match = resolvedUrl.pathname.match(
      /^\/api\/v1\/tasks\/([^/]+)\/artifacts\/([^/?#]+)/,
    );

    if (match === null) {
      return null;
    }

    return {
      taskId: match[1]!,
      artifactId: match[2]!,
      normalizedUrl: resolvedUrl.toString(),
    };
  } catch {
    return null;
  }
}

export function isAllowedArtifactUrl(url: string, taskId: string) {
  const match = parseArtifactUrl(url);

  return match !== null && match.taskId === taskId;
}

export function mergeArtifactsById(...artifactSets: ArtifactSummary[][]) {
  const artifactsById = new Map<string, ArtifactSummary>();

  for (const artifactSet of artifactSets) {
    for (const artifact of artifactSet) {
      artifactsById.set(artifact.artifact_id, artifact);
    }
  }

  return Array.from(artifactsById.values());
}

export function findLatestArtifactBySource(args: {
  taskId: string;
  src: string;
  streamArtifacts: ArtifactSummary[];
  deliveryArtifacts: ArtifactSummary[];
}) {
  const parsedSource = parseArtifactUrl(args.src);

  if (parsedSource === null || parsedSource.taskId !== args.taskId) {
    return null;
  }

  return (
    args.deliveryArtifacts.find(
      (artifact) => artifact.artifact_id === parsedSource.artifactId,
    ) ??
    args.streamArtifacts.find(
      (artifact) => artifact.artifact_id === parsedSource.artifactId,
    ) ??
    null
  );
}

export function findLatestArtifactById(args: {
  artifactId: string;
  streamArtifacts: ArtifactSummary[];
  deliveryArtifacts: ArtifactSummary[];
}) {
  return (
    args.deliveryArtifacts.find(
      (artifact) => artifact.artifact_id === args.artifactId,
    ) ??
    args.streamArtifacts.find(
      (artifact) => artifact.artifact_id === args.artifactId,
    ) ??
    null
  );
}
