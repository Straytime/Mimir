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

type AnchorStates<TAnchorKey extends string> = Record<
  TAnchorKey,
  {
    isVisible: boolean;
    signal: string | null;
  }
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
  anchorOrder: readonly TAnchorKey[],
  anchorRefs: AnchorRefs<TAnchorKey>,
  anchorStates: AnchorStates<TAnchorKey>,
  anchorTargets?: AnchorTargets<TAnchorKey>,
) {
  const previousAnchorStatesRef = useRef<AnchorStates<TAnchorKey> | null>(null);

  useLayoutEffect(() => {
    const changedAnchors = anchorOrder.filter((anchor) => {
      const currentState = anchorStates[anchor];

      if (!currentState.isVisible || currentState.signal === null) {
        return false;
      }

      const previousStates = previousAnchorStatesRef.current;

      if (previousStates === null) {
        return true;
      }

      const previousState = previousStates[anchor];

      return (
        previousState.isVisible !== currentState.isVisible ||
        previousState.signal !== currentState.signal
      );
    });
    const nextAnchorStates = anchorOrder.reduce<AnchorStates<TAnchorKey>>(
      (states, anchor) => {
        states[anchor] = anchorStates[anchor];
        return states;
      },
      {} as AnchorStates<TAnchorKey>,
    );

    if (changedAnchors.length === 0) {
      previousAnchorStatesRef.current = nextAnchorStates;
      return;
    }

    const activeAnchor = changedAnchors[0];
    const rootTarget = anchorRefs[activeAnchor]?.current;

    if (rootTarget === null || rootTarget === undefined) {
      return;
    }

    const target = resolveAnchorTarget(
      rootTarget,
      anchorTargets?.[activeAnchor]?.selector,
    );

    scrollCardIntoAnchorBand(target);
    previousAnchorStatesRef.current = nextAnchorStates;
  }, [anchorOrder, anchorRefs, anchorStates, anchorTargets]);
}
