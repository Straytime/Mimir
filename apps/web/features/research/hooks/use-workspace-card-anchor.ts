"use client";

import { useLayoutEffect, useRef, type RefObject } from "react";

import { RESEARCH_CARD_ANCHOR_GAP_PX } from "../utils/layout-vars";

type AnchorRefs<TAnchorKey extends string> = Record<
  TAnchorKey,
  RefObject<HTMLElement | null>
>;

function scrollCardIntoAnchorBand(target: HTMLElement) {
  const root = target.closest("main");

  if (!(root instanceof HTMLElement)) {
    return;
  }

  const statusBar = root.querySelector<HTMLElement>(
    "[data-research-status-bar='true']",
  );
  const statusBarBottom = statusBar?.getBoundingClientRect().bottom ?? 0;
  const nextTop =
    window.scrollY +
    target.getBoundingClientRect().top -
    statusBarBottom -
    RESEARCH_CARD_ANCHOR_GAP_PX;

  window.scrollTo({
    top: Math.max(0, Math.floor(nextTop)),
    behavior: "smooth",
  });
}

export function useWorkspaceCardAnchor<TAnchorKey extends string>(
  activeAnchor: TAnchorKey | null,
  anchorRefs: AnchorRefs<TAnchorKey>,
) {
  const previousAnchorRef = useRef<TAnchorKey | null>(null);

  useLayoutEffect(() => {
    if (activeAnchor === null || previousAnchorRef.current === activeAnchor) {
      return;
    }

    const target = anchorRefs[activeAnchor]?.current;

    if (target === null || target === undefined) {
      return;
    }

    scrollCardIntoAnchorBand(target);
    previousAnchorRef.current = activeAnchor;
  }, [activeAnchor, anchorRefs]);
}
