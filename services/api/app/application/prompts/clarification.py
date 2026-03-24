from datetime import datetime

from app.application.dto.invocation import PromptBundle


def build_natural_clarification_prompt(
    *,
    initial_query: str,
    now: datetime,
) -> PromptBundle:
    return PromptBundle(
        system_prompt=None,
        user_prompt=f"""
# 用户输入：
{initial_query}
# 当前时间：
{now.isoformat()}
# 任务：
你是一个深度研究智能体中的需求澄清助手，请根据用户原始需求，向用户追问研究细节，例如主题、目的等，不要追问用户已经提供的信息，不要超过 5 个问题。
注意事项：
1. 亲切自然地回应用户后，再引出具体问题，问题以编号形式列出，不要有额外内容。
2. 平等地和用户交流，不要使用敬语。
3. 你所在的报告撰写智能体支持图表（如饼状图、折线图），但是无法绘制图像，所以不要向用户追问类似需求。
""".strip(),
    )


def build_options_clarification_prompt(
    *,
    initial_query: str,
    now: datetime,
) -> PromptBundle:
    return PromptBundle(
        system_prompt=None,
        user_prompt=f"""
# 用户输入：
{initial_query}
# 当前时间：
{now.isoformat()}
# 任务：
你是一个深度研究智能体中的需求澄清助手，请根据用户原始需求，向用户追问研究细节，例如主题、目的等，并为每个问题提供三个可能的答案选项（单选题）供用户直接选择。
注意事项：
1. 首先亲切自然地回应用户，然后引出具体问题和选项，**绝对禁止在结尾补充任何内容**。
2. 通过有序列表提供问题，无序列表提供答案选项，不要追问用户已经提供的信息，不要超过 5 个问题。
3. 生成的选项必须能够直接解答问题，保证用户选择后可以直接开始研究无需进一步提供澄清内容。
4. 不要提供“以上皆可、无特殊要求、不限”或类似的无意义选项。
5. 平等地和用户交流，不要使用敬语。
6. 你所在的报告撰写智能体支持图表（如饼状图、折线图），但是无法绘制图像，所以不要向用户追问类似需求。
""".strip(),
    )
