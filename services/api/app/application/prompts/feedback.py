from datetime import datetime

import json

from app.application.dto.feedback import FeedbackAnalysisInput
from app.application.dto.invocation import PromptBundle


def build_feedback_analysis_prompt(
    *,
    analysis_input: FeedbackAnalysisInput,
    now: datetime,
) -> PromptBundle:
    previous_detail = json.dumps(
        analysis_input.previous_requirement_detail.model_dump(
            mode="json",
            exclude_none=True,
            exclude={"raw_llm_output"},
        ),
        ensure_ascii=False,
        indent=2,
    )
    return PromptBundle(
        system_prompt=f"""
<背景>
你是一个研究报告撰写智能体中的需求分析器，，现在是{now.isoformat()}。
<上一轮研究需求></上一轮研究需求>中是用户上一轮的研究报告需求；
<本次调整意见></本次调整意见>中是用户本轮的最新消息。
</背景>
<任务>
请结合用户上一轮的研究需求和本轮最新消息，重新深入分析然后汇总输出具体的用户需求。
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
<上一轮研究需求>
{previous_detail}
</上一轮研究需求>
<本次调整意见>
{analysis_input.feedback_text}
</本次调整意见>
""".strip(),
    )
