"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { ArtifactSummary } from "@/lib/contracts";

import { useResearchSessionStore } from "../providers/research-workspace-providers";
import { useDeliveryRefresh } from "../hooks/use-delivery-refresh";
import {
  findLatestArtifactById,
  findLatestArtifactBySource,
  isAllowedArtifactUrl,
} from "../utils/task-artifact";

type TaskArtifactImageProps = {
  alt: string;
  artifactId?: string | null;
  sourceUrl: string;
};

const EMPTY_ARTIFACTS: ArtifactSummary[] = [];

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

export function TaskArtifactImage({
  alt,
  artifactId,
  sourceUrl,
}: TaskArtifactImageProps) {
  const taskId = useResearchSessionStore((state) => state.session.taskId);
  const streamArtifacts = useResearchSessionStore((state) => state.stream.artifacts);
  const delivery = useResearchSessionStore((state) => state.remote.delivery);
  const refreshingDelivery = useResearchSessionStore(
    (state) => state.deliveryUi.refreshingDelivery,
  );
  const refreshDelivery = useDeliveryRefresh();
  const deliveryArtifacts = delivery?.artifacts ?? EMPTY_ARTIFACTS;

  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");

  const latestArtifact = useMemo(() => {
    if (taskId === null) {
      return null;
    }

    if (artifactId) {
      return findLatestArtifactById({
        artifactId,
        streamArtifacts,
        deliveryArtifacts,
      });
    }

    return findLatestArtifactBySource({
      taskId,
      src: sourceUrl,
      streamArtifacts,
      deliveryArtifacts,
    });
  }, [artifactId, deliveryArtifacts, sourceUrl, streamArtifacts, taskId]);

  const resolvedUrl = latestArtifact?.url ?? sourceUrl;
  const previousBlobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (previousBlobUrlRef.current !== null) {
        URL.revokeObjectURL(previousBlobUrlRef.current);
        previousBlobUrlRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (taskId === null || !isAllowedArtifactUrl(resolvedUrl, taskId)) {
      setStatus("error");
      setBlobUrl(null);
      return;
    }

    const currentTaskId = taskId;
    let cancelled = false;

    async function loadImage(targetUrl: string, allowRefresh: boolean) {
      setStatus("loading");

      try {
        const response = await fetch(targetUrl, {
          method: "GET",
        });

        if (response.ok) {
          const nextBlobUrl = URL.createObjectURL(await response.blob());

          if (cancelled) {
            URL.revokeObjectURL(nextBlobUrl);
            return;
          }

          if (previousBlobUrlRef.current !== null) {
            URL.revokeObjectURL(previousBlobUrlRef.current);
          }

          previousBlobUrlRef.current = nextBlobUrl;
          setBlobUrl(nextBlobUrl);
          setStatus("loaded");
          return;
        }

        const errorCode = await readErrorCode(response);

        if (
          allowRefresh &&
          !refreshingDelivery &&
          response.status === 401 &&
          errorCode === "access_token_invalid"
        ) {
          const detail = await refreshDelivery();
          const nextArtifact =
            artifactId === null || artifactId === undefined
              ? findLatestArtifactBySource({
                  taskId: currentTaskId,
                  src: targetUrl,
                  streamArtifacts,
                  deliveryArtifacts:
                    detail?.delivery?.artifacts ?? deliveryArtifacts,
                })
              : findLatestArtifactById({
                  artifactId,
                  streamArtifacts,
                  deliveryArtifacts:
                    detail?.delivery?.artifacts ?? deliveryArtifacts,
                });
          const nextUrl = nextArtifact?.url ?? null;

          if (nextUrl !== null && nextUrl !== targetUrl) {
            return;
          }
        }
      } catch {
        if (cancelled) {
          return;
        }
      }

      if (!cancelled) {
        setBlobUrl(null);
        setStatus("error");
      }
    }

    void loadImage(resolvedUrl, true);

    return () => {
      cancelled = true;
    };
  }, [
    artifactId,
    deliveryArtifacts,
    refreshDelivery,
    refreshingDelivery,
    resolvedUrl,
    retryNonce,
    sourceUrl,
    streamArtifacts,
    taskId,
  ]);

  if (taskId === null || !isAllowedArtifactUrl(resolvedUrl, taskId)) {
    return null;
  }

  if (status === "loading") {
    return (
      <div className="aspect-[16/10] animate-pulse bg-surface-container-high" />
    );
  }

  if (status === "error" || blobUrl === null) {
    return (
      <div className="bg-surface-container-high p-4">
        <p className="text-sm font-medium text-[#FFB86C]">交付链接已失效</p>
        <p className="mt-2 text-sm leading-6 text-secondary">
          当前图片链接不可用。请刷新交付链接后重试。
        </p>
        <button
          className="mt-4 bg-transparent px-4 py-2 text-sm font-semibold text-primary shadow-ghost transition hover:shadow-glow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint disabled:cursor-not-allowed disabled:text-tertiary disabled:shadow-none"
          disabled={refreshingDelivery}
          onClick={() => {
            setRetryNonce((currentNonce) => currentNonce + 1);
          }}
          type="button"
        >
          重试图片
        </button>
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      alt={alt}
      className="h-full w-full object-cover"
      src={blobUrl!}
    />
  );
}
