"use client";

import { useResearchSessionStore } from "../providers/research-workspace-providers";

const EXAMPLES = [
  "2025 年全球 AI 搜索产品竞争格局：主要玩家、商业模式与市场趋势",
  "远程办公对企业生产力的影响：最新研究综述与管理建议",
  "新能源汽车电池技术路线对比：磷酸铁锂 vs 三元锂 vs 固态电池",
] as const;

export function ExamplePrompts() {
  const setInitialPromptDraft = useResearchSessionStore(
    (state) => state.setInitialPromptDraft,
  );

  return (
    <div className="space-y-3">
      <p className="text-[11px] font-ui font-medium uppercase tracking-[0.15em] text-tertiary">
        示例研究主题
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        {EXAMPLES.map((example) => (
          <button
            className="bg-surface-container-lowest px-4 py-4 text-left text-sm leading-6 text-secondary shadow-ghost transition hover:bg-surface-container-high hover:shadow-glow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-surface-tint"
            key={example}
            onClick={() => setInitialPromptDraft(example)}
            type="button"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
