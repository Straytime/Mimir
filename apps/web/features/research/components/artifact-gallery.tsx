"use client";

import { useMemo } from "react";

import type { ArtifactSummary } from "@/lib/contracts";

import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { mergeArtifactsById } from "../utils/task-artifact";
import { TaskArtifactImage } from "./task-artifact-image";

const EMPTY_ARTIFACTS: ArtifactSummary[] = [];

export function ArtifactGallery() {
  const streamArtifacts = useResearchSessionStore((state) => state.stream.artifacts);
  const delivery = useResearchSessionStore((state) => state.remote.delivery);
  const deliveryArtifacts = delivery?.artifacts ?? EMPTY_ARTIFACTS;

  const artifacts = useMemo(
    () => mergeArtifactsById(streamArtifacts, deliveryArtifacts),
    [deliveryArtifacts, streamArtifacts],
  );

  return (
    <section
      aria-label="图库"
      className="bg-surface-container-low p-6"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-tertiary">
            Artifact Gallery
          </p>
          <h3 className="mt-3 text-xl font-semibold text-primary">配图制品</h3>
        </div>
        <span className="bg-surface-container-high px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-secondary">
          {artifacts.length} 张
        </span>
      </div>

      {artifacts.length === 0 ? (
        <div className="mt-4 bg-surface-container-lowest px-4 py-5 text-sm leading-7 text-tertiary">
          配图生成后会在这里显示缩略图与当前可用链接。
        </div>
      ) : (
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {artifacts.map((artifact) => (
            <article
              className="overflow-hidden bg-surface-container-lowest"
              key={artifact.artifact_id}
            >
              <div className="aspect-[16/10] bg-surface-container-high p-3">
                <TaskArtifactImage
                  alt={artifact.filename}
                  artifactId={artifact.artifact_id}
                  sourceUrl={artifact.url}
                />
              </div>
              <div className="px-4 py-4">
                <p className="text-sm font-semibold text-primary">
                  {artifact.filename}
                </p>
                <p className="mt-1 text-xs uppercase tracking-[0.12em] text-tertiary">
                  {artifact.mime_type}
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
