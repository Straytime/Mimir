import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

type TestProvidersProps = {
  children: ReactNode;
};

function TestProviders({ children }: TestProvidersProps) {
  return <>{children}</>;
}

export function renderWithStore(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, {
    wrapper: TestProviders,
    ...options,
  });
}
