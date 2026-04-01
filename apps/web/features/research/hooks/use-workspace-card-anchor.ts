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
  anchorSignal: string | null,
) {
  const previousAnchorRef = useRef<{
    anchor: TAnchorKey | null;
    signal: string | null;
  }>({
    anchor: null,
    signal: null,
  });

  useLayoutEffect(() => {
    if (
      activeAnchor === null ||
      (previousAnchorRef.current.anchor === activeAnchor &&
        previousAnchorRef.current.signal === anchorSignal)
    ) {
      return;
    }

    const target = anchorRefs[activeAnchor]?.current;

    if (target === null || target === undefined) {
      return;
    }

    scrollCardIntoAnchorBand(target);
    previousAnchorRef.current = {
      anchor: activeAnchor,
      signal: anchorSignal,
    };
  }, [activeAnchor, anchorRefs, anchorSignal]);
}
