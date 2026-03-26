"use client";

import type { RequirementDetail } from "@/lib/contracts";

type RequirementSummaryCardProps = {
  requirementDetail: RequirementDetail | null;
};

export function RequirementSummaryCard({
  requirementDetail,
}: RequirementSummaryCardProps) {
  return (
    <article className="bg-surface-container-low px-5 py-5">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-tertiary">
        {requirementDetail === null ? "Requirement Summary" : "需求摘要已生成"}
      </p>

      {requirementDetail === null ? (
        <div className="mt-4 bg-surface-container-lowest px-4 py-4 text-sm leading-7 text-tertiary">
          分析完成后，研究目标、范围、输出格式与语言要求会固定在这里。
        </div>
      ) : (
        <>
          <h3 className="mt-3 text-xl font-semibold text-primary">
            {requirementDetail.research_goal}
          </h3>
          <dl className="mt-4 space-y-3 text-sm leading-6 text-secondary">
            <div>
              <dt className="font-medium text-tertiary">领域</dt>
              <dd>{requirementDetail.domain}</dd>
            </div>
            <div>
              <dt className="font-medium text-tertiary">细化说明</dt>
              <dd>{requirementDetail.requirement_details}</dd>
            </div>
            <div>
              <dt className="font-medium text-tertiary">输出格式</dt>
              <dd>{requirementDetail.output_format}</dd>
            </div>
            <div>
              <dt className="font-medium text-tertiary">语言</dt>
              <dd>{requirementDetail.language}</dd>
            </div>
          </dl>
        </>
      )}
    </article>
  );
}
