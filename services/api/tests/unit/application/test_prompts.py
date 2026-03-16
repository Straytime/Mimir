from datetime import UTC, datetime

from app.application.prompts.clarification import (
    build_natural_clarification_prompt,
    build_options_clarification_prompt,
)
from app.application.prompts.requirement import build_requirement_analysis_prompt
from app.application.services.clarification import AnalysisInput, ClarificationAnswerSet


NOW = datetime(2026, 3, 16, 9, 30, tzinfo=UTC)


def test_natural_clarification_prompt_keeps_required_fields_and_constraints() -> None:
    prompt = build_natural_clarification_prompt(
        initial_query="帮我研究中国 AI 搜索产品竞争格局和未来机会",
        client_timezone="Asia/Shanghai",
        client_locale="zh-CN",
        now=NOW,
    )

    assert "帮我研究中国 AI 搜索产品竞争格局和未来机会" in prompt
    assert "Asia/Shanghai" in prompt
    assert "zh-CN" in prompt
    assert "2026-03-16T09:30:00+00:00" in prompt
    assert "只输出面向用户的自然语言澄清问题" in prompt
    assert "不要输出 JSON" in prompt


def test_options_clarification_prompt_keeps_required_fields_and_constraints() -> None:
    prompt = build_options_clarification_prompt(
        initial_query="帮我研究中国 AI 搜索产品竞争格局和未来机会",
        client_timezone="Asia/Shanghai",
        client_locale="zh-CN",
        now=NOW,
    )

    assert "帮我研究中国 AI 搜索产品竞争格局和未来机会" in prompt
    assert "Asia/Shanghai" in prompt
    assert "zh-CN" in prompt
    assert "2026-03-16T09:30:00+00:00" in prompt
    assert "1 到 5 个问题" in prompt
    assert "不要生成 o_auto" in prompt
    assert "只输出问题和选项正文" in prompt


def test_requirement_analysis_prompt_keeps_required_fields_and_constraints() -> None:
    prompt = build_requirement_analysis_prompt(
        analysis_input=AnalysisInput(
            initial_query="帮我研究中国 AI 搜索产品竞争格局和未来机会",
            clarification_mode="options",
            clarification_answer_set=ClarificationAnswerSet(
                natural_answer=None,
                selected_options=[
                    {
                        "question": "更偏向哪个方向？",
                        "selected_label": "主要参与者与格局",
                    }
                ],
                submitted_by_timeout=False,
            ),
        ),
        client_timezone="Asia/Shanghai",
        client_locale="zh-CN",
        now=NOW,
    )

    assert "帮我研究中国 AI 搜索产品竞争格局和未来机会" in prompt
    assert "主要参与者与格局" in prompt
    assert "Asia/Shanghai" in prompt
    assert "zh-CN" in prompt
    assert "2026-03-16T09:30:00+00:00" in prompt
    assert '"research_goal"' in prompt
    assert '"freshness_requirement"' in prompt
    assert "只输出合法 JSON" in prompt
