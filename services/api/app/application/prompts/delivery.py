from app.application.dto.delivery import OutlineInvocation, WriterInvocation


def build_outline_prompt(*, invocation: OutlineInvocation) -> str:
    source_lines = "\n".join(
        f"- {source.refer}: {source.title}\n  {source.info}"
        for source in invocation.formatted_sources
    )
    return (
        "你是研究输出准备器。请基于 RequirementDetail 和已去重来源，"
        "生成合法 JSON，根节点为 \"research_outline\"。\n"
        f"当前时间: {invocation.now.isoformat()}\n"
        f"研究目标: {invocation.requirement_detail.research_goal}\n"
        f"领域: {invocation.requirement_detail.domain}\n"
        f"细化要求: {invocation.requirement_detail.requirement_details}\n"
        "输出 JSON 必须包含 \"title\"、\"sections\"、\"entities\"。\n"
        "只输出合法 JSON，不要输出解释。\n"
        "来源摘要:\n"
        f"{source_lines}"
    )


def build_writer_prompt(*, invocation: WriterInvocation) -> str:
    section_lines = "\n".join(
        f"- {section.order}. {section.title}: {section.description}"
        for section in invocation.outline.sections
    )
    source_lines = "\n".join(
        f"- {source.refer}: {source.title}\n  {source.info}"
        for source in invocation.formatted_sources
    )
    return (
        "你是研究报告 writer。请根据大纲和来源，输出结构化正文增量输出与最终 markdown。\n"
        f"当前时间: {invocation.now.isoformat()}\n"
        f"研究目标: {invocation.requirement_detail.research_goal}\n"
        f"大纲标题: {invocation.outline.title}\n"
        "大纲章节:\n"
        f"{section_lines}\n"
        "可引用来源:\n"
        f"{source_lines}\n"
        "只有在确实需要图表时才调用 python_interpreter；如需图表才调用。\n"
        "不要在没有必要时生成工具调用。"
    )
