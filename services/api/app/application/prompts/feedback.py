from datetime import datetime

from app.application.dto.feedback import FeedbackAnalysisInput


def build_feedback_analysis_prompt(
    *,
    analysis_input: FeedbackAnalysisInput,
    client_timezone: str,
    client_locale: str,
    now: datetime,
) -> str:
    previous_detail = analysis_input.previous_requirement_detail.model_dump(
        mode="json",
        exclude_none=True,
        exclude={"raw_llm_output"},
    )
    return f"""
你是 Mimir 的反馈需求分析器。
当前时间: {now.isoformat()}
用户时区: {client_timezone}
用户语言: {client_locale}
原始需求: {analysis_input.initial_query}
上一轮 RequirementDetail: {previous_detail}
用户反馈: {analysis_input.feedback_text}

请基于上一轮 RequirementDetail 与本次反馈，生成新的 RequirementDetail。
请只输出合法 JSON，且必须包含以下字段：
- "research_goal"
- "domain"
- "requirement_details"
- "output_format"
- "freshness_requirement"
- "language"

不要输出 Markdown 代码块，不要输出额外解释。
""".strip()
