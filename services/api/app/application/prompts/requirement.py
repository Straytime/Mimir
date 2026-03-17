from datetime import datetime
from typing import TYPE_CHECKING

from app.application.dto.invocation import PromptBundle

if TYPE_CHECKING:
    from app.application.services.clarification import AnalysisInput


def build_requirement_analysis_prompt(
    *,
    analysis_input: "AnalysisInput",
    now: datetime,
) -> PromptBundle:
    clarification_content = analysis_input.clarification_answer_text()
    return PromptBundle(
        system_prompt=f"""
<背景>
你是一个研究报告撰写智能体中的需求分析器，<历史需求沟通></历史需求沟通>中是研究助手和用户的需求沟通记录，现在是{now.isoformat()}。
</背景>
<任务>
请根据历史需求沟通中的内容，深入分析然后汇总输出具体的用户需求。
注意事项：
1. 必须严格依据历史沟通内容进行分析
2. 必须给出明确、具体、无歧义的分析结果，严禁出现模棱两可的推测。
3. 按以下维度进行输出
- 核心研究目标
- 研究主题所属的垂域
- 需求明细：仅限用户主动表达或反馈的需求细项（如有），绝对禁止自行杜撰、篡改、曲解！必须包含研究使用语言的分析，默认中文
- 适用的研究输出格式（单选）：["通用","研究报告","商业报告","专业论文","深度文章","指南攻略","购物推荐"]
- 是否对参考信息有高时效需求：是 or 否
4. 直接输出结果，不要解释或询问。
</任务>

<输出格式>
```json
{{
"研究目标":"",
"所属垂域":"",
"需求明细":"",
"适用形式":"",
"时效需求":""
}}
```
</输出格式>
""".strip(),
        user_prompt=f"""
<历史需求沟通>
user：{analysis_input.initial_query}
assistant：{analysis_input.clarification_output}
user: {clarification_content}
</历史需求沟通>
""".strip(),
    )
