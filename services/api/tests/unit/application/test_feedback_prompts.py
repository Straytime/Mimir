from datetime import UTC, datetime

from app.application.dto.feedback import FeedbackAnalysisInput
from app.application.prompts.feedback import build_feedback_analysis_prompt
from app.domain.enums import FreshnessRequirement, OutputFormat
from app.domain.schemas import RequirementDetail


NOW = datetime(2026, 3, 16, 18, 30, tzinfo=UTC)


def build_requirement_detail() -> RequirementDetail:
    return RequirementDetail(
        research_goal="分析中国 AI 搜索产品的竞争格局与未来机会",
        domain="互联网 / AI 产品",
        requirement_details="偏商业报告，关注中国市场，覆盖近两年变化。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )


def test_feedback_prompt_matches_prd_literal_system_user_split() -> None:
    prompt = build_feedback_analysis_prompt(
        analysis_input=FeedbackAnalysisInput(
            initial_query="请分析中国 AI 搜索产品的竞争格局。",
            previous_requirement_detail=build_requirement_detail(),
            feedback_text="补充比较各家产品在 B 端场景的落地情况，并删掉不够确定的推测。",
        ),
        now=NOW,
    )

    assert "<背景>" in prompt.system_prompt
    assert "你是一个研究报告撰写智能体中的需求分析器" in prompt.system_prompt
    assert "现在是2026-03-16T18:30:00+00:00。" in prompt.system_prompt
    assert "<上一轮研究需求></上一轮研究需求>中是用户上一轮的研究报告需求" in prompt.system_prompt
    assert "<本次调整意见></本次调整意见>中是用户本轮的最新消息" in prompt.system_prompt
    assert '"研究目标"' in prompt.system_prompt
    assert '"适用形式"' in prompt.system_prompt

    assert "<上一轮研究需求>" in prompt.user_prompt
    assert "分析中国 AI 搜索产品的竞争格局与未来机会" in prompt.user_prompt
    assert "<本次调整意见>" in prompt.user_prompt
    assert "补充比较各家产品在 B 端场景的落地情况" in prompt.user_prompt
    assert prompt.messages[0].role == "system"
    assert prompt.messages[1].role == "user"
