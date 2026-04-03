"use client";

import { Children, isValidElement, useDeferredValue } from "react";
import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";

import type { ArtifactSummary } from "@/lib/contracts";

import { useReportAutoScroll } from "../hooks/use-report-auto-scroll";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { fmt02 } from "../utils/format";
import { RESEARCH_CARD_MAX_HEIGHT_STYLE_VALUE } from "../utils/layout-vars";
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
    <div className="my-6 overflow-hidden bg-surface-container-low p-3">
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

function ReportMarkdownLink(props: ComponentPropsWithoutRef<"a">) {
  const linkProps = props as ComponentPropsWithoutRef<"a"> & Record<string, unknown>;

  if (Object.prototype.hasOwnProperty.call(linkProps, "data-footnote-backref")) {
    return null;
  }

  const { children, href, ...rest } = props;

  return (
    <a
      href={href}
      rel="noreferrer noopener"
      target="_blank"
      {...rest}
    >
      {children}
    </a>
  );
}

export function ReportCanvas() {
  const snapshot = useResearchSessionStore((state) => state.remote.snapshot);
  const delivery = useResearchSessionStore((state) => state.remote.delivery);
  const outline = useResearchSessionStore((state) => state.stream.outline);
  const outlineReady = useResearchSessionStore((state) => state.stream.outlineReady);
  const reportMarkdown = useResearchSessionStore(
    (state) => state.stream.reportMarkdown,
  );

  const deferredReportMarkdown = useDeferredValue(reportMarkdown);
  const {
    handleScroll,
    scrollContainerRef,
    scrollToBottom,
    showScrollToBottom,
  } = useReportAutoScroll({
    contentKey: `${outlineReady}:${outline?.sections.length ?? 0}:${deferredReportMarkdown.length}`,
    phase: snapshot?.phase ?? "clarifying",
  });

  if (snapshot === null) {
    return null;
  }

  const shouldShowSkeleton = deferredReportMarkdown.trim().length === 0;

  return (
    <section
      aria-label="报告画布"
      className="flex flex-col overflow-hidden bg-surface-container-low p-6"
      style={{
        height: RESEARCH_CARD_MAX_HEIGHT_STYLE_VALUE,
        maxHeight: RESEARCH_CARD_MAX_HEIGHT_STYLE_VALUE,
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
            Report Canvas
          </p>
          <p className="mt-sp-2 text-sm leading-6 text-secondary">
            {getReportPhaseCopy(snapshot.phase)}
          </p>
        </div>

        {delivery ? (
          <div className="flex flex-wrap gap-2">
            <span className="bg-surface-container-high px-3 py-1 text-[11px] font-ui font-medium uppercase tracking-[0.15em] text-secondary">
              {fmt02(delivery.artifact_count)} 张配图
            </span>
          </div>
        ) : null}
      </div>

      <div className="relative mt-6 flex min-h-0 flex-1">
        <div
          aria-label="报告正文"
          className="flex-1 min-h-0 overflow-y-auto bg-surface-container-lowest px-5 py-5"
          onScroll={handleScroll}
          ref={scrollContainerRef}
          role="region"
        >
          {shouldShowSkeleton ? (
            <div className="space-y-3">
              <div className="relative h-4 w-2/3 overflow-hidden bg-surface-container-high">
                <div className="absolute inset-0 animate-scan bg-gradient-to-b from-transparent via-primary/10 to-transparent" />
              </div>
              <div className="relative h-4 w-full overflow-hidden bg-surface-container-high">
                <div className="absolute inset-0 animate-scan bg-gradient-to-b from-transparent via-primary/10 to-transparent" />
              </div>
              <div className="relative h-4 w-5/6 overflow-hidden bg-surface-container-high">
                <div className="absolute inset-0 animate-scan bg-gradient-to-b from-transparent via-primary/10 to-transparent" />
              </div>
              <p className="pt-3 text-sm leading-6 text-secondary">
                报告正文将在撰写开始后逐步显示。
              </p>
            </div>
          ) : (
            <div className="prose prose-lab max-w-none font-narrative leading-[1.6] text-secondary">
              <ReactMarkdown
                components={{
                  a: ReportMarkdownLink,
                  img: ReportMarkdownImage,
                  p: ReportParagraph,
                }}
                rehypePlugins={[[rehypeSanitize, REPORT_MARKDOWN_SANITIZE_SCHEMA]]}
                remarkPlugins={[remarkGfm]}
                skipHtml
                urlTransform={allowCanonicalArtifactPath}
              >
                {deferredReportMarkdown}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {showScrollToBottom ? (
          <button
            className="absolute bottom-4 right-4 bg-primary px-4 py-2 text-sm font-semibold text-on-primary transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
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
