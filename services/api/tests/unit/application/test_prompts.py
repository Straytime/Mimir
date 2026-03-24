from datetime import UTC, datetime

from app.application.prompts.clarification import (
    build_natural_clarification_prompt,
    build_options_clarification_prompt,
)
from app.application.prompts.requirement import build_requirement_analysis_prompt
from app.application.services.clarification import AnalysisInput, ClarificationAnswerSet


NOW = datetime(2026, 3, 16, 9, 30, tzinfo=UTC)


def _normalize(value: str) -> str:
    return "\n".join(line.strip() for line in value.strip().splitlines())


def test_natural_clarification_prompt_matches_prd_literal_contract() -> None:
    prompt = build_natural_clarification_prompt(
        initial_query="帮我研究中国 AI 搜索产品竞争格局和未来机会",
        now=NOW,
    )

    assert prompt.system_prompt is None
    assert _normalize(prompt.user_prompt) == _normalize(
        """
        # 用户输入：
        帮我研究中国 AI 搜索产品竞争格局和未来机会
        # 当前时间：
        2026-03-16T09:30:00+00:00
        # 任务：
        你是一个深度研究智能体中的需求澄清助手，请根据用户原始需求，向用户追问研究细节，例如主题、目的等，不要追问用户已经提供的信息，不要超过 5 个问题。
        注意事项：
        1. 亲切自然地回应用户后，再引出具体问题，问题以编号形式列出，不要有额外内容。
        2. 平等地和用户交流，不要使用敬语。
        3. 你所在的报告撰写智能体支持图表（如饼状图、折线图），但是无法绘制图像，所以不要向用户追问类似需求。
        """
    )
    assert len(prompt.messages) == 1
    assert prompt.messages[0].role == "user"
    assert prompt.messages[0].content == prompt.user_prompt


def test_options_clarification_prompt_matches_prd_literal_contract() -> None:
    prompt = build_options_clarification_prompt(
        initial_query="帮我研究中国 AI 搜索产品竞争格局和未来机会",
        now=NOW,
    )

    assert prompt.system_prompt is None
    assert _normalize(prompt.user_prompt) == _normalize(
        """
        # 用户输入：
        帮我研究中国 AI 搜索产品竞争格局和未来机会
        # 当前时间：
        2026-03-16T09:30:00+00:00
        # 任务：
        你是一个深度研究智能体中的需求澄清助手，请根据用户原始需求，向用户追问研究细节，例如主题、目的等，并为每个问题提供三个可能的答案选项（单选题）供用户直接选择。
        注意事项：
        1. 首先亲切自然地回应用户，然后引出具体问题和选项，**绝对禁止在结尾补充任何内容**。
        2. 通过有序列表提供问题，无序列表提供答案选项，不要追问用户已经提供的信息，不要超过 5 个问题。
        3. 生成的选项必须能够直接解答问题，保证用户选择后可以直接开始研究无需进一步提供澄清内容。
        4. 不要提供“以上皆可、无特殊要求、不限”或类似的无意义选项。
        5. 平等地和用户交流，不要使用敬语。
        6. 你所在的报告撰写智能体支持图表（如饼状图、折线图），但是无法绘制图像，所以不要向用户追问类似需求。
        """
    )
    assert len(prompt.messages) == 1
    assert prompt.messages[0].role == "user"
    assert prompt.messages[0].content == prompt.user_prompt


def test_requirement_analysis_prompt_matches_prd_literal_system_user_split() -> None:
    prompt = build_requirement_analysis_prompt(
        analysis_input=AnalysisInput(
            initial_query="帮我研究中国 AI 搜索产品竞争格局和未来机会",
            clarification_mode="options",
            clarification_output=(
                "1. 你更想聚焦哪个方向？\n"
                "- 主要参与者与格局\n"
                "- 产品能力与体验\n"
                "- 商业化机会"
            ),
            clarification_answer_set=ClarificationAnswerSet(
                natural_answer=None,
                selected_options=[
                    {
                        "question": "你更想聚焦哪个方向？",
                        "selected_label": "主要参与者与格局",
                    }
                ],
                submitted_by_timeout=False,
            ),
        ),
        now=NOW,
    )

    assert "<背景>" in prompt.system_prompt
    assert "你是一个研究报告撰写智能体中的需求分析器" in prompt.system_prompt
    assert "<历史需求沟通></历史需求沟通>中是研究助手和用户的需求沟通记录" in prompt.system_prompt
    assert "现在是2026-03-16T09:30:00+00:00。" in prompt.system_prompt
    assert "<输出格式>" in prompt.system_prompt
    assert '"研究目标"' in prompt.system_prompt
    assert '"时效需求"' in prompt.system_prompt

    assert _normalize(prompt.user_prompt) == _normalize(
        """
        <历史需求沟通>
        user：帮我研究中国 AI 搜索产品竞争格局和未来机会
        assistant：1. 你更想聚焦哪个方向？
        - 主要参与者与格局
        - 产品能力与体验
        - 商业化机会
        user: 主要参与者与格局
        </历史需求沟通>
        """
    )


def test_requirement_analysis_prompt_skips_auto_option_from_user_history() -> None:
    prompt = build_requirement_analysis_prompt(
        analysis_input=AnalysisInput(
            initial_query="帮我研究中国 AI 搜索产品竞争格局和未来机会",
            clarification_mode="options",
            clarification_output="1. 你更想聚焦哪个方向？\n- 自动\n- 主要参与者与格局",
            clarification_answer_set=ClarificationAnswerSet(
                natural_answer=None,
                selected_options=[
                    {
                        "question": "你更想聚焦哪个方向？",
                        "selected_label": "自动",
                    }
                ],
                submitted_by_timeout=True,
            ),
        ),
        now=NOW,
    )

    assert "assistant：" in prompt.user_prompt
    assert "user:" in prompt.user_prompt
    assert "自动" not in prompt.user_prompt.split("user:", maxsplit=1)[1]
