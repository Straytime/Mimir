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
    <div className="space-y-3">
      <p className="text-[11px] font-ui font-medium uppercase tracking-[0.15em] text-tertiary">
        示例研究主题
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        {EXAMPLES.map((example) => (
          <button
            className="relative overflow-hidden bg-surface-container-lowest px-4 py-4 text-left text-sm leading-6 text-secondary outline outline-1 outline-transparent transition-[background-color,color,outline-color] duration-150 before:absolute before:inset-y-0 before:left-0 before:w-px before:bg-surface-tint before:opacity-0 before:transition-opacity before:duration-150 hover:bg-surface-container-low hover:text-primary hover:outline-outline-variant/15 hover:before:opacity-100 focus-visible:bg-surface-container-low focus-visible:text-primary focus-visible:outline-surface-tint/25 focus-visible:before:opacity-100 data-[active=true]:before:opacity-100"
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
    </div>
  );
}
