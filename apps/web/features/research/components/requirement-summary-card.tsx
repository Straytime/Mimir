"use client";

import type { RequirementDetail } from "@/lib/contracts";

type RequirementSummaryCardProps = {
  requirementDetail: RequirementDetail | null;
};

export function RequirementSummaryCard({
  requirementDetail,
}: RequirementSummaryCardProps) {
  if (requirementDetail === null) {
    return null;
  }

  return (
    <article
      className="bg-surface-container-low px-5 py-5"
      data-research-anchor-target="requirement-summary-content"
    >
      <p className="text-[11px] font-ui font-semibold uppercase tracking-[0.15em] text-tertiary">
        需求摘要已生成
      </p>
      <h3 className="mt-sp-2 text-xl font-narrative font-semibold text-primary">
        {requirementDetail.research_goal}
      </h3>
      <dl className="mt-4 space-y-sp-2 text-sm leading-6 text-secondary">
        <div>
          <dt className="font-ui font-medium text-tertiary">领域</dt>
          <dd className="font-narrative">{requirementDetail.domain}</dd>
        </div>
        <div>
          <dt className="font-ui font-medium text-tertiary">细化说明</dt>
          <dd className="font-narrative">{requirementDetail.requirement_details}</dd>
        </div>
        <div>
          <dt className="font-ui font-medium text-tertiary">输出格式</dt>
          <dd className="font-narrative">{requirementDetail.output_format}</dd>
        </div>
        <div>
          <dt className="font-ui font-medium text-tertiary">语言</dt>
          <dd className="font-narrative">{requirementDetail.language}</dd>
        </div>
      </dl>
    </article>
  );
}
