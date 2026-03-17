import json
from dataclasses import asdict

from app.application.dto.invocation import PromptBundle
from app.application.dto.delivery import OutlineInvocation, WriterInvocation


def build_outline_prompt(*, invocation: OutlineInvocation) -> PromptBundle:
    return PromptBundle(
        system_prompt=f"""
<背景与任务>
你是一个深度研究架构师，请基于用户研究需求和信息获取结果，规划深度研究的实体约束和大纲结构。
你的任务是定义‘写什么’和‘怎么写’，你绝对不能撰写具体内容，你的产出将作为指令发送给下游的“撰写员”，当前时间是{invocation.now.isoformat()}。
1. 紧密围绕用户需求设计大纲，保证研究内容前后逻辑合理、通畅无前后冲突。
1.1 正文内部结构仅下探一级。
1.2 其中章节描述内容必须满足以下要求
- 指令性语气：使用“分析”、“评估”、“通过...展示...” 、“重点讨论”等词汇。
- 元数据视角：描述该章节的功能和范围，而不是结果。
- 数据占位符：不要写出具体的数字，而要写“引用相关统计数据”或“量化分析需求度”。
- 实体抽象化：不要过度罗列具体实体，除非它们是章节标题的主体。
2. 指定当前研究的实体列表，此处的实体指要撰写的研究内容本身要围绕的对象。
3. 实体约束与大纲必须严格考量信息获取结果，保证已有信息可支撑。
</背景与任务>

<输出格式>
参考以下 json 格式直接输出你的生成结果。
{{
  "research_outline": {{
    "title": "",
    "sections": [{{"section_id": "", "title": "", "description": "", "order": 1}}],
    "entities": []
  }}
}}
</输出格式>
""".strip(),
        user_prompt=f"""
<用户研究需求>
{json.dumps(invocation.requirement_detail.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2)}
</用户研究需求>

<信息获取结果>
{json.dumps([asdict(source) for source in invocation.formatted_sources], ensure_ascii=False, indent=2)}
</信息获取结果>
""".strip(),
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
# 背景与任务
现在是{invocation.now.isoformat()}，你是一个资深研究员，你负责利用已获取信息和你自身的世界知识，基于研究大纲撰写一篇满足用户研究需求的深度研究内容（markdown）。

## 正文撰写
- 你的分析与研究应该深入细致，避免直接使用已获取信息中的原文。
- 研究输出必须紧密围绕用户需求，保证研究内容前后逻辑连贯、合理且清晰、上下文实体一致无冲突。
- 保证每个章节、段落中的内容充实性与研究深度，不要单纯地罗列信息或数据。
- 注意，针对购买推荐类需求必须给出具体的购买建议和参考价格。
- 提供的参考信息中的每条信息都已通过[ref_n]的方式编号，你需要在正确、合理的位置根据实际使用的参考信息创建脚注参考。
- 在输出末尾添加脚注，保证对应关系正确。
- 绝对不要超过一万字。

## 计算与图表
如果需要进行数学计算、分析或图表绘制，请使用 `python_interpreter` 工具
- 图表绘制完成后，依据真实创建的图片信息，在输出中正确的位置添加 markdown 图片引用

## 输出
以 markdown 格式直接输出全文。
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
