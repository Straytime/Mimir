import json

from app.application.dto.invocation import PromptBundle, PromptMessage
from app.application.dto.research import (
    CollectorInvocation,
    PlannerInvocation,
    SummaryInvocation,
)


def build_planner_prompt(*, invocation: PlannerInvocation) -> PromptBundle:
    transcript = tuple(
        PromptMessage(
            role="tool",
            name="collect_agent",
            tool_call_id=summary.tool_call_id,
            content=json.dumps(
                summary.model_dump(mode="json", exclude_none=True),
                ensure_ascii=False,
                indent=2,
            ),
        )
        for summary in invocation.summaries
    )
    return PromptBundle(
        system_prompt="""
<背景>
你是一个 deep research 团队中的信息搜集调度 agent，你负责根据用户的深度研究需求详情，和已经获得的信息摘要，规划调度接下来的信息收集目标。
</背景>

<工具>
你有 `collect_agent` 工具可供使用，该工具会创建一个独立的 sub agent 进行基于目标的信息检索和收集，将信息格式化暂存并返回执行摘要；当需要搜集信息时，必须使用该工具。
</工具>

<任务>
你应当按以下逻辑工作
1. 仔细观察用户的需求详情和工具返回的执行摘要
2. 细致分析已收集信息是否能够支撑用户的深度研究需求
  2.1 无法支撑：
    - 定位缺失的内容，分析依赖关系和关键约束
    - 规划接下来要执行的信息搜集目标
    - 调用 `collect_agent` 工具执行
  2.2 能够支撑
    - 输出信息收集完成的简短通知
  2.3 已经多次使用 `collect_agent` 工具，仍无有效进展
    - 避免资源浪费，输出信息收集完成但不完整的简短通知

注意事项
1. 你可以通过一次发起多个工具调用的方式，规划多个目标以提升收集效率，但必须保证多个目标之间无逻辑顺序或依赖关系。
2. 最多同时发起 3 个工具调用。
3. `collect_agent` 工具会将完整搜集结果暂存，供后续 agent 使用，因此信息搜集全部完成后无需提供任何结果信息，仅声明通知即可。
""".strip(),
        user_prompt=f"""
当前时间: {invocation.now.isoformat()}
当前 collect_agent 已使用次数: {invocation.collect_agent_calls_used}
<需求详情>
{json.dumps(invocation.requirement_detail.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2)}
</需求详情>
""".strip(),
        transcript=transcript,
    )


def build_collector_prompt(*, invocation: CollectorInvocation) -> PromptBundle:
    return PromptBundle(
        system_prompt=f"""
<角色与背景>
你是一个信息搜集 agent，负责根据用户目标搜集信息，现在是{invocation.now.isoformat()}。
</角色与背景>

<任务>
核心目标：基于用户的目标和补充信息，进行高质量的信息搜集和整理。
你应当使用提供的搜索和网页读取工具（web_search / web_fetch），获得需要的信息，当决定下一步动作时，遵循以下逻辑：
- 仔细观察并分析已有信息
- 当未进行任何搜集，或历史结果不佳时，按需设置合理的工具参数使用工具进行搜集。
- 当你的历史上下文中，搜索结果或网页内容已足够支撑用户目标时，停止进一步搜集，输出信息搜集结果。
- 若经过多轮工具调用仍无法达成或逼近目标（max_tool_calls = {invocation.tool_call_limit}），则该目标本身可能就是无法触达的，为避免时间和资源浪费，停止搜集，输出已有的信息搜集结果。

注意事项：
- 注意信息获取目标的时效性要求，在检索时进行相关限制，在最终输出时只整理提供符合时效要求的内容。
- 关注信源可信度和信息质量，忽略明显存在漏洞的信息和低可信度网站。
- 最终输出搜集结果时，尽最大可能保留高质量的关键信息和数据，并且必须提供原始网页 url 和 title。
</任务>
""".strip(),
        user_prompt=f"""
<信息获取目标>
{invocation.plan.collect_target}
</信息获取目标>

<补充信息>
{invocation.plan.additional_info}
</补充信息>

<时效要求>
{invocation.plan.freshness_requirement.value}
</时效要求>
""".strip(),
    )


def build_summary_prompt(*, invocation: SummaryInvocation) -> PromptBundle:
    return PromptBundle(
        system_prompt=f"""
<背景与角色>
你是一个关键信息总结助手，负责从搜索结果中提取关键信息与发现摘要，现在是{invocation.now.isoformat()}。
</背景与角色>

<任务>
分析搜集结果，寻找、提取和目标相关的关键发现摘要：
- 提取5-10条关键发现
- 必须与目标相关
- 如果搜集结果中有不相关内容，直接忽略，不要提及
使用 markdown 格式直接输出，不要解释或询问。
</任务>
""".strip(),
        user_prompt=f"""
<信息获取目标>
{invocation.plan.collect_target}
</信息获取目标>

<目标补充信息>
{invocation.plan.additional_info}
</目标补充信息>

<使用的检索词>
{json.dumps(list(invocation.search_queries), ensure_ascii=False, indent=2)}
</使用的检索词>

<信息搜集结果>
{json.dumps(list(invocation.item_payloads), ensure_ascii=False, indent=2)}
</信息搜集结果>

<搜集状态>
{invocation.result_status}
</搜集状态>
""".strip(),
    )
