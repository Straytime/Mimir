"use client";

import { useLayoutEffect, type RefObject } from "react";

import {
  RESEARCH_CARD_ANCHOR_GAP_PX,
  RESEARCH_CARD_MAX_HEIGHT_CSS_VAR,
  RESEARCH_STATUS_BAR_HEIGHT_CSS_VAR,
} from "../utils/layout-vars";

function measureWorkspaceBodyMaxHeight(root: HTMLElement) {
  const statusBar = root.querySelector<HTMLElement>(
    "[data-research-status-bar='true']",
  );
  const inputBar = root.querySelector<HTMLElement>(
    "[data-research-input-bar='true']",
  );

  if (statusBar === null || inputBar === null) {
    root.style.removeProperty(RESEARCH_CARD_MAX_HEIGHT_CSS_VAR);
    root.style.removeProperty(RESEARCH_STATUS_BAR_HEIGHT_CSS_VAR);
    return;
  }

  const statusBarHeight = statusBar.getBoundingClientRect().height;
  const inputBarHeight = inputBar.getBoundingClientRect().height;
  const viewportHeight = window.innerHeight;
  const availableHeight =
    viewportHeight -
    statusBarHeight -
    inputBarHeight -
    RESEARCH_CARD_ANCHOR_GAP_PX * 2;

  root.style.setProperty(
    RESEARCH_CARD_MAX_HEIGHT_CSS_VAR,
    `${Math.max(0, Math.floor(availableHeight))}px`,
  );
  root.style.setProperty(
    RESEARCH_STATUS_BAR_HEIGHT_CSS_VAR,
    `${Math.max(0, Math.ceil(statusBarHeight))}px`,
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

    const statusBar = root.querySelector<HTMLElement>(
      "[data-research-status-bar='true']",
    );
    const inputBar = root.querySelector<HTMLElement>(
      "[data-research-input-bar='true']",
    );

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
      root.style.removeProperty(RESEARCH_STATUS_BAR_HEIGHT_CSS_VAR);
    };
  }, [isActiveWorkspace, rootRef]);
}
