"use client";

import { useState } from "react";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const EXAMPLES = [
  "从心理学角度解析 openclaw 爆火的原因",
  "一级方程式赛车 26 年新规的争议与影响",
  "新能源汽车电池技术路线对比：磷酸铁锂 vs 三元锂 vs 固态电池",
] as const;

export function ExamplePrompts() {
  const setInitialPromptDraft = useResearchSessionStore(
    (state) => state.setInitialPromptDraft,
  );
  const [activeExample, setActiveExample] = useState<string | null>(null);

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {EXAMPLES.map((example) => (
        <button
          className="relative overflow-hidden bg-surface-container px-4 py-4 text-left text-sm leading-6 text-secondary transition-[background-color,color] duration-150 before:absolute before:inset-y-0 before:left-0 before:w-px before:bg-primary before:opacity-0 before:transition-opacity before:duration-150 hover:bg-surface-container-high hover:text-primary hover:before:opacity-100 focus-visible:bg-surface-container-high focus-visible:text-primary focus-visible:before:opacity-100 focus-visible:shadow-[0_0_0_2px_rgba(255,173,58,0.2)] data-[active=true]:before:opacity-100"
          data-active={activeExample === example}
          key={example}
          onBlur={() => setActiveExample((current) => (current === example ? null : current))}
          onClick={() => setInitialPromptDraft(example)}
          onFocus={() => setActiveExample(example)}
          onMouseEnter={() => setActiveExample(example)}
          onMouseLeave={() =>
            setActiveExample((current) => (current === example ? null : current))
          }
          type="button"
        >
          {example}
        </button>
      ))}
    </div>
  );
}
