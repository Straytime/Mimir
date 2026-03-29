"use client";

import { useCallback, useRef, useState } from "react";

import { useDeliveryRefresh } from "../hooks/use-delivery-refresh";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import {
  selectCanDownloadMarkdown,
  selectCanDownloadPdf,
} from "../store/selectors";
import { fmt02 } from "../utils/format";

type CopyState = "idle" | "copied" | "error";

function useCopyMarkdown() {
  const reportMarkdown = useResearchSessionStore(
    (state) => state.stream.reportMarkdown,
  );
  const [copyState, setCopyState] = useState<CopyState>("idle");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const copyMarkdown = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(reportMarkdown);
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }

    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      setCopyState("idle");
      timerRef.current = null;
    }, 2_000);
  }, [reportMarkdown]);

  return { copyState, copyMarkdown };
}

function getCopyButtonLabel(copyState: CopyState) {
  if (copyState === "copied") {
    return "已复制 ✓";
  }

  if (copyState === "error") {
    return "复制失败";
  }

  return "复制 Markdown";
}

type DownloadFormat = "markdown" | "pdf";

async function readErrorCode(response: Response) {
  try {
    const responseJson = (await response.clone().json()) as {
      error?: { code?: string };
    };

    return responseJson.error?.code ?? null;
  } catch {
    return null;
  }
}

function createDownloadFilename(format: DownloadFormat) {
  return format === "markdown" ? "report-markdown.zip" : "report.pdf";
}

export function DeliveryActions() {
  const phase = useResearchSessionStore(
    (state) => state.remote.snapshot?.phase ?? null,
  );
  const delivery = useResearchSessionStore((state) => state.remote.delivery);
  const refreshingDelivery = useResearchSessionStore(
    (state) => state.deliveryUi.refreshingDelivery,
  );
  const markdownDownloadState = useResearchSessionStore(
    (state) => state.deliveryUi.markdownDownloadState,
  );
  const pdfDownloadState = useResearchSessionStore(
    (state) => state.deliveryUi.pdfDownloadState,
  );
  const setDownloadState = useResearchSessionStore(
    (state) => state.setDownloadState,
  );
  const revisionTransition = useResearchSessionStore(
    (state) => state.ui.revisionTransition,
  );
  const canDownloadMarkdown = useResearchSessionStore(selectCanDownloadMarkdown);
  const canDownloadPdf = useResearchSessionStore(selectCanDownloadPdf);
  const reset = useResearchSessionStore((state) => state.reset);
  const refreshDelivery = useDeliveryRefresh();
  const { copyState, copyMarkdown } = useCopyMarkdown();

  const [deliveryError, setDeliveryError] = useState<string | null>(null);

  if (phase !== "delivered") {
    return null;
  }

  async function downloadDelivery(
    format: DownloadFormat,
    url: string | null,
    allowRefresh = true,
  ) {
    if (url === null) {
      return;
    }

    setDeliveryError(null);
    setDownloadState({
      format,
      state: "loading",
    });

    try {
      const response = await fetch(url, {
        method: "GET",
      });

      if (!response.ok) {
        const errorCode = await readErrorCode(response);

        if (
          allowRefresh &&
          response.status === 401 &&
          errorCode === "access_token_invalid"
        ) {
          const detail = await refreshDelivery();
          const refreshedUrl =
            format === "markdown"
              ? detail?.delivery?.markdown_zip_url ?? null
              : detail?.delivery?.pdf_url ?? null;

          if (refreshedUrl !== null && refreshedUrl !== url) {
            await downloadDelivery(format, refreshedUrl, false);
            return;
          }
        }

        throw new Error("delivery_unavailable");
      }

      const blobUrl = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");

      anchor.href = blobUrl;
      anchor.download = createDownloadFilename(format);
      anchor.click();
      URL.revokeObjectURL(blobUrl);

      setDownloadState({
        format,
        state: "idle",
      });
    } catch {
      setDownloadState({
        format,
        state: "error",
      });
      setDeliveryError("交付链接已失效或任务已清理。");
    } finally {
      setDownloadState({
        format,
        state: "idle",
      });
    }
  }

  return (
    <section
      aria-label="交付操作"
      className="bg-surface-container-low p-6"
    >
      <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
        Delivery
      </p>
      <div className="mt-sp-2 flex flex-wrap items-center gap-3 text-sm">
        <span className="bg-surface-container-high px-3 py-1 text-[11px] font-ui font-medium uppercase tracking-[0.15em] text-secondary">
          {fmt02(delivery?.artifact_count ?? 0)} 张配图
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <button
          className="bg-transparent px-4 py-3 text-sm font-semibold text-primary shadow-ghost transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:text-tertiary disabled:shadow-none"
          disabled={!canDownloadMarkdown}
          onClick={() => {
            void copyMarkdown();
          }}
          type="button"
        >
          {getCopyButtonLabel(copyState)}
        </button>
        <button
          className="bg-transparent px-4 py-3 text-sm font-semibold text-primary shadow-ghost transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:text-tertiary disabled:shadow-none"
          disabled={
            delivery === null ||
            refreshingDelivery ||
            markdownDownloadState === "loading" ||
            !canDownloadMarkdown
          }
          onClick={() => {
            void downloadDelivery("markdown", delivery?.markdown_zip_url ?? null);
          }}
          type="button"
        >
          {markdownDownloadState === "loading"
            ? "下载中..."
            : "下载 Markdown Zip"}
        </button>
        <button
          className="bg-transparent px-4 py-3 text-sm font-semibold text-primary shadow-ghost transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:text-tertiary disabled:shadow-none"
          disabled={
            delivery === null ||
            refreshingDelivery ||
            pdfDownloadState === "loading" ||
            !canDownloadPdf
          }
          onClick={() => {
            void downloadDelivery("pdf", delivery?.pdf_url ?? null);
          }}
          type="button"
        >
          {pdfDownloadState === "loading" ? "下载中..." : "下载 PDF"}
        </button>
      </div>

      {!canDownloadMarkdown || !canDownloadPdf ? (
        <p className="mt-4 text-sm leading-6 text-secondary">
          {revisionTransition.status !== "idle"
            ? "新一轮研究正在接管，当前交付链接已锁定。"
            : "报告已生成，下载将在反馈阶段开放。"}
        </p>
      ) : null}

      {deliveryError ? (
        <p className="mt-4 text-sm leading-6 text-[#FF6B6B]">{deliveryError}</p>
      ) : null}

      <div className="mt-6 border-t border-outline-variant pt-6">
        <button
          className="bg-primary px-5 py-3 text-sm font-semibold text-on-primary transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint"
          onClick={reset}
          type="button"
        >
          开始新研究
        </button>
      </div>
    </section>
  );
}
