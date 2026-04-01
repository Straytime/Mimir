"use client";

import { useLayoutEffect, useRef, type RefObject } from "react";

import { RESEARCH_CARD_ANCHOR_GAP_PX } from "../utils/layout-vars";

type AnchorRefs<TAnchorKey extends string> = Record<
  TAnchorKey,
  RefObject<HTMLElement | null>
>;

type AnchorTargets<TAnchorKey extends string> = Partial<
  Record<
    TAnchorKey,
    {
      selector: string;
    }
  >
>;

function resolveVisibleBottom(element: HTMLElement | null) {
  if (element === null) {
    return null;
  }

  const rect = element.getBoundingClientRect();

  if (rect.height <= 0 && rect.width <= 0) {
    return null;
  }

  return rect.bottom;
}

function scrollCardIntoAnchorBand(target: HTMLElement) {
  const root = target.closest("main");

  if (!(root instanceof HTMLElement)) {
    return;
  }

  const topStack = root.querySelector<HTMLElement>(
    "[data-research-top-stack='true']",
  );
  const statusBar = root.querySelector<HTMLElement>(
    "[data-research-status-bar='true']",
  );
  const topStackBottom =
    resolveVisibleBottom(topStack) ??
    resolveVisibleBottom(statusBar) ??
    0;
  const nextTop =
    window.scrollY +
    target.getBoundingClientRect().top -
    topStackBottom -
    RESEARCH_CARD_ANCHOR_GAP_PX;

  window.scrollTo({
    top: Math.max(0, Math.floor(nextTop)),
    behavior: "smooth",
  });
}

function resolveAnchorTarget(
  rootTarget: HTMLElement,
  selector: string | undefined,
) {
  if (selector === undefined) {
    return rootTarget;
  }

  const candidate = rootTarget.querySelector<HTMLElement>(selector);

  if (candidate === null) {
    return rootTarget;
  }

  const rect = candidate.getBoundingClientRect();

  if (rect.height <= 0 && rect.width <= 0) {
    return rootTarget;
  }

  return candidate;
}

export function useWorkspaceCardAnchor<TAnchorKey extends string>(
  activeAnchor: TAnchorKey | null,
  anchorRefs: AnchorRefs<TAnchorKey>,
  anchorSignal: string | null,
  anchorTargets?: AnchorTargets<TAnchorKey>,
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

    const rootTarget = anchorRefs[activeAnchor]?.current;

    if (rootTarget === null || rootTarget === undefined) {
      return;
    }

    const target = resolveAnchorTarget(
      rootTarget,
      anchorTargets?.[activeAnchor]?.selector,
    );

    scrollCardIntoAnchorBand(target);
    previousAnchorRef.current = {
      anchor: activeAnchor,
      signal: anchorSignal,
    };
  }, [activeAnchor, anchorRefs, anchorSignal, anchorTargets]);
}
