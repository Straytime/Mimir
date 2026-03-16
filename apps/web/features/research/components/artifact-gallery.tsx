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
      className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            Artifact Gallery
          </p>
          <h3 className="mt-3 text-xl font-semibold text-slate-950">配图制品</h3>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
          {artifacts.length} 张
        </span>
      </div>

      {artifacts.length === 0 ? (
        <div className="mt-4 rounded-3xl border border-dashed border-slate-300 bg-slate-50/80 px-4 py-5 text-sm leading-7 text-slate-600">
          配图生成后会在这里显示缩略图与当前可用链接。
        </div>
      ) : (
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {artifacts.map((artifact) => (
            <article
              className="overflow-hidden rounded-3xl border border-slate-200 bg-white/90"
              key={artifact.artifact_id}
            >
              <div className="aspect-[16/10] bg-slate-100 p-3">
                <TaskArtifactImage
                  alt={artifact.filename}
                  artifactId={artifact.artifact_id}
                  sourceUrl={artifact.url}
                />
              </div>
              <div className="px-4 py-4">
                <p className="text-sm font-semibold text-slate-950">
                  {artifact.filename}
                </p>
                <p className="mt-1 text-xs uppercase tracking-[0.12em] text-slate-500">
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
