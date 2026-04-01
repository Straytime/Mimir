"use client";

import { useLayoutEffect, type RefObject } from "react";

import {
  RESEARCH_CARD_ANCHOR_GAP_PX,
  RESEARCH_CARD_MAX_HEIGHT_CSS_VAR,
} from "../utils/layout-vars";

function resolveVisibleHeight(element: HTMLElement | null) {
  if (element === null) {
    return null;
  }

  const rect = element.getBoundingClientRect();

  if (rect.height <= 0 && rect.width <= 0) {
    return null;
  }

  return rect.height;
}

function measureWorkspaceBodyMaxHeight(root: HTMLElement) {
  const topStack = root.querySelector<HTMLElement>(
    "[data-research-top-stack='true']",
  );
  const statusBar = root.querySelector<HTMLElement>(
    "[data-research-status-bar='true']",
  );
  const inputBar = root.querySelector<HTMLElement>(
    "[data-research-input-bar='true']",
  );

  if ((topStack === null && statusBar === null) || inputBar === null) {
    root.style.removeProperty(RESEARCH_CARD_MAX_HEIGHT_CSS_VAR);
    return;
  }

  const topStackHeight =
    resolveVisibleHeight(topStack) ??
    resolveVisibleHeight(statusBar) ??
    0;
  const inputBarHeight = inputBar.getBoundingClientRect().height;
  const viewportHeight = window.innerHeight;
  const availableHeight =
    viewportHeight -
    topStackHeight -
    inputBarHeight -
    RESEARCH_CARD_ANCHOR_GAP_PX * 2;

  root.style.setProperty(
    RESEARCH_CARD_MAX_HEIGHT_CSS_VAR,
    `${Math.max(0, Math.floor(availableHeight))}px`,
  );
}

export function useWorkspaceBodyMaxHeight(
  rootRef: RefObject<HTMLElement | null>,
  isActiveWorkspace: boolean,
) {
  useLayoutEffect(() => {
    const root = rootRef.current;

    if (root === null) {
      return;
    }

    const update = () => {
      measureWorkspaceBodyMaxHeight(root);
    };

    update();

    const resizeObserver =
      typeof ResizeObserver === "function"
        ? new ResizeObserver(() => {
            update();
          })
        : null;

    const topStack = root.querySelector<HTMLElement>(
      "[data-research-top-stack='true']",
    );
    const statusBar = root.querySelector<HTMLElement>(
      "[data-research-status-bar='true']",
    );
    const inputBar = root.querySelector<HTMLElement>(
      "[data-research-input-bar='true']",
    );

    if (topStack !== null) {
      resizeObserver?.observe(topStack);
    }

    if (statusBar !== null) {
      resizeObserver?.observe(statusBar);
    }

    if (inputBar !== null) {
      resizeObserver?.observe(inputBar);
    }

    window.addEventListener("resize", update);

    return () => {
      window.removeEventListener("resize", update);
      resizeObserver?.disconnect();
      root.style.removeProperty(RESEARCH_CARD_MAX_HEIGHT_CSS_VAR);
    };
  }, [isActiveWorkspace, rootRef]);
}
