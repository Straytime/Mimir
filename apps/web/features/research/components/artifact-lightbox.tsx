"use client";

import { useCallback, useEffect } from "react";

import type { ArtifactSummary } from "@/lib/contracts";

import { TaskArtifactImage } from "./task-artifact-image";

type ArtifactLightboxProps = {
  artifact: ArtifactSummary;
  onClose: () => void;
};

async function downloadArtifact(artifact: ArtifactSummary) {
  try {
    const response = await fetch(artifact.url, { method: "GET" });

    if (!response.ok) {
      return;
    }

    const blobUrl = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a");

    anchor.href = blobUrl;
    anchor.download = artifact.filename;
    anchor.click();
    URL.revokeObjectURL(blobUrl);
  } catch {
    // download silently fails
  }
}

export function ArtifactLightbox({ artifact, onClose }: ArtifactLightboxProps) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleKeyDown]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
      data-testid="lightbox-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="relative max-h-[90vh] max-w-[90vw] bg-surface-container-low p-6">
        <button
          aria-label="关闭"
          className="absolute right-3 top-3 px-2 py-1 text-lg text-secondary transition hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint"
          onClick={onClose}
          type="button"
        >
          ×
        </button>

        <div className="max-h-[70vh] overflow-auto">
          <TaskArtifactImage
            alt={artifact.filename}
            artifactId={artifact.artifact_id}
            sourceUrl={artifact.url}
          />
        </div>

        <div className="mt-4">
          <p className="text-sm font-semibold text-primary">
            {artifact.filename}
          </p>
          <p className="mt-1 text-[11px] font-ui uppercase tracking-[0.15em] text-tertiary">
            {artifact.mime_type}
          </p>
        </div>

        <button
          className="mt-4 bg-transparent px-4 py-3 text-sm font-semibold text-primary shadow-ghost transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint"
          onClick={() => {
            void downloadArtifact(artifact);
          }}
          type="button"
        >
          下载
        </button>
      </div>
    </div>
  );
}
