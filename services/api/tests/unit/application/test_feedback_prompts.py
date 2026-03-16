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


def test_feedback_prompt_invariants_cover_previous_requirement_and_feedback_delta() -> None:
    prompt = build_feedback_analysis_prompt(
        analysis_input=FeedbackAnalysisInput(
            initial_query="请分析中国 AI 搜索产品的竞争格局。",
            previous_requirement_detail=build_requirement_detail(),
            feedback_text="补充比较各家产品在 B 端场景的落地情况，并删掉不够确定的推测。",
        ),
        client_timezone="Asia/Shanghai",
        client_locale="zh-CN",
        now=NOW,
    )

    assert "请分析中国 AI 搜索产品的竞争格局。" in prompt
    assert "分析中国 AI 搜索产品的竞争格局与未来机会" in prompt
    assert "补充比较各家产品在 B 端场景的落地情况" in prompt
    assert "2026-03-16T18:30:00+00:00" in prompt
    assert '"research_goal"' in prompt
    assert '"requirement_details"' in prompt
    assert "只输出合法 JSON" in prompt
