from app.application.dto.invocation import InvocationProfile, ToolSchema
from app.core.config import Settings


def build_stage_profile(settings: Settings, stage: str) -> InvocationProfile:
    if stage == "clarification_natural":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_clarification_natural_model,
            temperature=0.5,
            top_p=0.8,
            max_tokens=98304,
            thinking=False,
            clear_thinking=None,
            stream=True,
        )
    if stage == "clarification_options":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_clarification_options_model,
            temperature=0.5,
            top_p=0.8,
            max_tokens=98304,
            thinking=False,
            clear_thinking=None,
            stream=True,
        )
    if stage == "requirement_analysis":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_requirement_analyzer_model,
            temperature=0.5,
            top_p=0.8,
            max_tokens=98304,
            thinking=False,
            clear_thinking=None,
            stream=True,
        )
    if stage == "planner":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_planner_model,
            temperature=1,
            top_p=1,
            max_tokens=98304,
            thinking=True,
            clear_thinking=False,
            stream=True,
        )
    if stage == "collector":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_collector_model,
            temperature=1,
            top_p=1,
            max_tokens=98304,
            thinking=True,
            clear_thinking=False,
            stream=True,
        )
    if stage == "summary":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_summary_model,
            temperature=0.6,
            top_p=0.8,
            max_tokens=98304,
            thinking=False,
            clear_thinking=None,
            stream=True,
        )
    if stage == "outline":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_outline_model,
            temperature=1,
            top_p=1,
            max_tokens=98304,
            thinking=True,
            clear_thinking=False,
            stream=True,
        )
    if stage == "writer":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_writer_model,
            temperature=1,
            top_p=1,
            max_tokens=98304,
            thinking=True,
            clear_thinking=False,
            stream=True,
        )
    if stage == "feedback_analysis":
        return InvocationProfile(
            stage=stage,
            model=settings.zhipu_feedback_analyzer_model,
            temperature=0.5,
            top_p=0.8,
            max_tokens=98304,
            thinking=False,
            clear_thinking=None,
            stream=True,
        )
    raise ValueError(f"Unsupported invocation stage: {stage}")


def build_collect_agent_tool_schema() -> ToolSchema:
    return ToolSchema(
        name="collect_agent",
        description=(
            "创建独立的信息收集 sub agent，针对单个明确的信息获取目标进行检索和搜集，"
            "执行完成后会自动将结果暂存，返回执行摘要"
        ),
        parameters={
            "collect_target": {
                "type": "string",
                "description": "信息获取目标",
            },
            "additional_info": {
                "type": "string",
                "description": "可辅助 sub agent、有助于其更快、更好达成收集目标的补充信息",
            },
            "freshness_requirement": {
                "type": "string",
                "enum": ["low", "high"],
                "description": "该搜集目标对参考信息的时效要求",
            },
        },
        required=("collect_target",),
    )


def build_web_search_tool_schema() -> ToolSchema:
    return ToolSchema(
        name="web_search",
        description="搜索工具，通过搜索引擎检索指定信息，返回搜索结果列表，包含网页摘要和对应 url",
        parameters={
            "search_query": {
                "type": "string",
                "description": "要搜索的关键词",
            },
            "search_recency_filter": {
                "type": "string",
                "enum": ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"],
                "description": "限定搜索结果的时间范围，最近一日、一周、一月、一年或不限制",
            },
        },
        required=("search_query",),
    )


def build_web_fetch_tool_schema() -> ToolSchema:
    return ToolSchema(
        name="web_fetch",
        description="网页读取工具，可读取 url 获取其内容",
        parameters={
            "url": {
                "type": "string",
                "description": "要读取的网页链接",
            }
        },
        required=("url",),
    )


def build_python_interpreter_tool_schema() -> ToolSchema:
    return ToolSchema(
        name="python_interpreter",
        description=(
            "执行 Python 代码进行数学计算、数据分析或图表绘制。代码应在隔离环境中运行，"
            "绘图请使用 matplotlib/seaborn 并将图表以 png 保存到当前目录"
        ),
        parameters={
            "code": {
                "type": "string",
                "description": "完整的 Python 代码",
            }
        },
        required=("code",),
    )
