"use client";

import { useState } from "react";

import { useDeliveryRefresh } from "../hooks/use-delivery-refresh";
import { useResearchSessionStore } from "../providers/research-workspace-providers";
import {
  selectCanDownloadMarkdown,
  selectCanDownloadPdf,
} from "../store/selectors";

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
  const refreshDelivery = useDeliveryRefresh();

  const [deliveryError, setDeliveryError] = useState<string | null>(null);

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
      className="rounded-[2rem] border border-slate-200/70 bg-white/82 p-6 shadow-sm backdrop-blur"
    >
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-tertiary">
        Delivery
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
        <span className="bg-surface-container-high px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-secondary">
          {delivery?.artifact_count ?? 0} 张配图
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <button
          className="border border-outline-variant/15 bg-transparent px-4 py-3 text-sm font-semibold text-primary transition hover:border-primary disabled:cursor-not-allowed disabled:border-tertiary disabled:text-tertiary"
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
          className="border border-outline-variant/15 bg-transparent px-4 py-3 text-sm font-semibold text-primary transition hover:border-primary disabled:cursor-not-allowed disabled:border-tertiary disabled:text-tertiary"
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
    </section>
  );
}
