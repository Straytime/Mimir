import json
from dataclasses import asdict

from app.application.dto.delivery import OutlineInvocation, WriterInvocation
from app.application.dto.invocation import PromptBundle


def _build_outline_system_prompt(now_iso: str) -> str:
    return f"""
<背景与任务>
你是一个深度研究架构师，请基于用户研究需求和信息获取结果，规划深度研究的实体约束和大纲结构。
你的任务是定义“写什么”和“怎么写”，你**绝对不能**撰写具体内容，你的产出将作为指令发送给下游的“撰写员”，当前时间是{now_iso}。
1. 紧密围绕用户需求设计大纲，保证研究内容前后逻辑合理、通畅无前后冲突。
1.1 正文内部结构仅下探一级。
1.2 其中章节描述内容**必须**满足以下要求
- 指令性语气：使用“分析”、“评估”、“通过...展示...”、“重点讨论”等词汇。
- 元数据视角：描述该章节的**功能**和**范围**，而不是**结果**。
- 数据占位符：不要写出具体的数字（如 “92%”），而要写“引用相关统计数据”或“量化分析需求度”。
- 实体抽象化：不要过度罗列具体实体，除非它们是章节标题的主体。应使用“选取代表性XX”、“对比主流XX”等抽象化表述。
2. 指定当前研究的实体列表，此处的实体指要撰写的研究内容本身要围绕的对象。
3. **实体约束与大纲必须严格考量信息获取结果，保证已有信息可支撑**。
<背景与任务>

<输出格式>
参考以下 json 格式直接输出你的生成结果。
{{
    "research_outline": {{
        "标题": {{
            "title": ""
        }},
        "section_1": {{
            "title": "",
            "description": ""
        }},
        ……
        "section_n": {{
            "title": "",
            "description": ""
        }},
        "参考来源": {{
            "title": "参考来源",
            "description": "列明所有参考来源"
        }}
    }},
    "entities": []
}}
</输出格式>
""".strip()


def build_outline_prompt(*, invocation: OutlineInvocation) -> PromptBundle:
    return PromptBundle(
        system_prompt=_build_outline_system_prompt(invocation.now.isoformat()),
        user_prompt=(
            "<用户研究需求>\n"
            + json.dumps(
                invocation.requirement_detail.model_dump(
                    mode="json", exclude_none=True
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n</用户研究需求>\n\n"
            + "<信息获取结果>\n"
            + json.dumps(
                [asdict(source) for source in invocation.formatted_sources],
                ensure_ascii=False,
                indent=2,
            )
            + "\n</信息获取结果>"
        ),
    )


def build_writer_prompt(*, invocation: WriterInvocation) -> PromptBundle:
    outline_payload = {
        "title": invocation.outline.title,
        "sections": [asdict(section) for section in invocation.outline.sections],
        "entities": list(invocation.outline.entities),
    }
    source_payload = [asdict(source) for source in invocation.formatted_sources]
    return PromptBundle(
        system_prompt=f"""
## 背景与任务
现在是{invocation.now.isoformat()}，你是一个资深研究员，你负责利用已获取信息和你自身的世界知识，基于研究大纲撰写一篇满足用户研究需求的深度研究内容（markdown）。

## 正文撰写
- 你的分析与研究应该深入细致，避免直接使用已获取信息中的原文。
- 研究输出必须紧密围绕用户需求，**保证研究内容前后逻辑连贯、合理且清晰、上下文实体一致无冲突。**
- 保证每个章节、段落中的内容充实性与研究深度，不要单纯地罗列信息或数据，更不能编造。
- 在输入信息支撑足够的情况下，积极使用图表来进行辅助可视化展示和分析，提升研究的说服力和可读性。但是严禁在没有足够信息支撑的情况下编造或强行拼凑图表。
- 注意，针对购买推荐类需求必须给出具体的购买建议和参考价格。
- 提供的参考信息中的每条信息都已进行编号，你需要在正确、合理的位置根据实际使用的参考信息插入角标，并在输出末尾添加脚注，保证对应关系正确。
- 若用户需求未指定撰写字数或输出长度，请根据研究复杂度和大纲，合理规划报告篇幅

## 计算与图表
如果需要进行数学计算、分析或图表绘制，请使用 `python_interpreter` 工具
- 图表绘制完成后，你会在 tool result 中收到真实的 `summary` 与 `artifacts[]` 元数据
- 如果 `artifacts[]` 非空，只能使用其中返回的 `canonical_path` 插入 markdown 图片引用，不能自行猜测图片路径
- 如果 `artifacts[]` 为空，仍可基于 `summary` 继续撰写，不要把“没有出图”输出成错误

## 输出
使用 GitHub Flavored Markdown 标准语法直接撰写输出全文。不要在最终输出中添加任何无关解释，例如“研究输出如下”、“以下是我的研究内容”等等。
""".strip(),
        user_prompt=f"""
<参考信息>
{json.dumps(source_payload, ensure_ascii=False, indent=2)}
</参考信息>

<研究需求>
{json.dumps(invocation.requirement_detail.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2)}
</研究需求>

<大纲与实体约束>
{json.dumps(outline_payload, ensure_ascii=False, indent=2)}
</大纲与实体约束>
""".strip(),
    )
