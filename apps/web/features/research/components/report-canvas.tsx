"use client";

import { Children, isValidElement, useDeferredValue } from "react";
import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

import type { ArtifactSummary } from "@/lib/contracts";

import { useReportAutoScroll } from "../hooks/use-report-auto-scroll";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { findLatestArtifactBySource } from "../utils/task-artifact";
import { TaskArtifactImage } from "./task-artifact-image";

const EMPTY_ARTIFACTS: ArtifactSummary[] = [];
const CANONICAL_ARTIFACT_PATH_PATTERN = /^mimir:\/\/artifact\/[^/?#]+$/;
const REPORT_MARKDOWN_SANITIZE_SCHEMA = {
  ...defaultSchema,
  protocols: {
    ...defaultSchema.protocols,
    src: [...(defaultSchema.protocols?.src ?? []), "mimir"],
  },
};

function allowCanonicalArtifactPath(url: string) {
  if (CANONICAL_ARTIFACT_PATH_PATTERN.test(url)) {
    return url;
  }

  return defaultUrlTransform(url);
}

function ReportMarkdownImage(props: ComponentPropsWithoutRef<"img">) {
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const streamArtifacts = useResearchSessionStore((state) => state.stream.artifacts);
  const delivery = useResearchSessionStore((state) => state.remote.delivery);
  const deliveryArtifacts = delivery?.artifacts ?? EMPTY_ARTIFACTS;

  if (typeof props.src !== "string" || taskId === null) {
    return null;
  }

  const latestArtifact = findLatestArtifactBySource({
    taskId,
    src: props.src,
    streamArtifacts,
    deliveryArtifacts,
  });

  if (latestArtifact === null) {
    return null;
  }

  return (
    <div className="my-6 overflow-hidden rounded-3xl border border-slate-200 bg-slate-50/80 p-3">
      <TaskArtifactImage
        alt={props.alt ?? latestArtifact.filename}
        artifactId={latestArtifact.artifact_id}
        sourceUrl={latestArtifact.url}
      />
    </div>
  );
}

function getReportPhaseCopy(phase: string) {
  switch (phase) {
    case "preparing_outline":
      return "正在构思报告结构";
    case "writing_report":
      return "正在撰写报告";
    case "delivered":
      return "报告已交付";
    default:
      return "正在准备报告";
  }
}

function ReportParagraph(props: ComponentPropsWithoutRef<"p">) {
  const normalizedChildren = Children.toArray(props.children).filter((child) => {
    return !(typeof child === "string" && child.trim().length === 0);
  });

  const rendersOnlyImage =
    normalizedChildren.length === 1 &&
    isValidElement(normalizedChildren[0]) &&
    normalizedChildren[0].type === ReportMarkdownImage;

  if (rendersOnlyImage) {
    return <div>{props.children}</div>;
  }

  return <p>{props.children}</p>;
}

export function ReportCanvas() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const currentRevision = useResearchSessionStore(
    (state) => state.remote.currentRevision,
  );
  const delivery = useResearchSessionStore((state) => state.remote.delivery);
  const outline = useResearchSessionStore((state) => state.stream.outline);
  const outlineReady = useResearchSessionStore((state) => state.stream.outlineReady);
  const reportMarkdown = useResearchSessionStore(
    (state) => state.stream.reportMarkdown,
  );

  const deferredReportMarkdown = useDeferredValue(reportMarkdown);
  const {
    autoScrollEnabled,
    bottomAnchorRef,
    handleScroll,
    scrollContainerRef,
    scrollToBottom,
  } = useReportAutoScroll(
    `${outlineReady}:${outline?.sections.length ?? 0}:${deferredReportMarkdown.length}`,
  );

  if (snapshot === null) {
    return null;
  }

  const shouldShowSkeleton = deferredReportMarkdown.trim().length === 0;

  return (
    <section
      aria-label="报告画布"
      className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            Report Canvas
          </p>
          <h3 className="mt-3 text-2xl font-semibold text-slate-950">
            第 {currentRevision?.revision_number ?? snapshot.active_revision_number} 轮报告
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {getReportPhaseCopy(snapshot.phase)}
          </p>
        </div>

        {delivery ? (
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-800">
              {delivery.artifact_count} 张配图
            </span>
          </div>
        ) : null}
      </div>

      {outlineReady && outline ? (
        <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50/80 px-5 py-5">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">
            Outline
          </p>
          <h4 className="mt-3 text-lg font-semibold text-slate-950">
            {outline.title}
          </h4>
          <ol className="mt-4 space-y-3">
            {outline.sections.map((section) => (
              <li key={section.section_id}>
                <p className="text-sm font-semibold text-slate-950">
                  {section.title}
                </p>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  {section.description}
                </p>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      <div className="relative mt-6">
        <div
          aria-label="报告正文"
          className="max-h-[34rem] overflow-y-auto rounded-3xl border border-slate-200 bg-white/90 px-5 py-5"
          onScroll={handleScroll}
          ref={scrollContainerRef}
          role="region"
        >
          {shouldShowSkeleton ? (
            <div className="space-y-3">
              <div className="h-4 w-2/3 animate-pulse rounded-full bg-slate-200/80" />
              <div className="h-4 w-full animate-pulse rounded-full bg-slate-200/80" />
              <div className="h-4 w-5/6 animate-pulse rounded-full bg-slate-200/80" />
              <p className="pt-3 text-sm leading-6 text-slate-600">
                报告正文将在 `writer.delta` 到达后逐步追加到这里。
              </p>
            </div>
          ) : (
            <div className="prose prose-slate max-w-none text-slate-800">
              <ReactMarkdown
                components={{
                  a: ({ children, href, ...props }) => (
                    <a
                      href={href}
                      rel="noreferrer noopener"
                      target="_blank"
                      {...props}
                    >
                      {children}
                    </a>
                  ),
                  img: ReportMarkdownImage,
                  p: ReportParagraph,
                }}
                rehypePlugins={[[rehypeSanitize, REPORT_MARKDOWN_SANITIZE_SCHEMA]]}
                skipHtml
                urlTransform={allowCanonicalArtifactPath}
              >
                {deferredReportMarkdown}
              </ReactMarkdown>
            </div>
          )}

          <div ref={bottomAnchorRef} />
        </div>

        {!autoScrollEnabled ? (
          <button
            className="absolute bottom-4 right-4 rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white shadow-lg"
            onClick={scrollToBottom}
            type="button"
          >
            回到底部
          </button>
        ) : null}
      </div>
    </section>
  );
}
