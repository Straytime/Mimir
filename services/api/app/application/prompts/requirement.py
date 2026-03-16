from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application.services.clarification import AnalysisInput


def build_requirement_analysis_prompt(
    *,
    analysis_input: "AnalysisInput",
    client_timezone: str,
    client_locale: str,
    now: datetime,
) -> str:
    selected_options_block = "\n".join(
        f'- {item["question"]}: {item["selected_label"]}'
        for item in analysis_input.clarification_answer_set.selected_options
    )
    return f"""
你是 Mimir 的需求分析器。
当前时间: {now.isoformat()}
用户时区: {client_timezone}
用户语言: {client_locale}
原始需求: {analysis_input.initial_query}
澄清模式: {analysis_input.clarification_mode}
自然语言补充: {analysis_input.clarification_answer_set.natural_answer}
结构化选择:
{selected_options_block or "- 无"}
是否由超时自动提交: {analysis_input.clarification_answer_set.submitted_by_timeout}

请只输出合法 JSON，且必须包含以下字段：
- "research_goal"
- "domain"
- "requirement_details"
- "output_format"
- "freshness_requirement"
- "language"

不要输出 Markdown 代码块，不要输出额外解释。
""".strip()
