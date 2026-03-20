from datetime import UTC, datetime

from app.application.dto.delivery import (
    OutlineInvocation,
    OutlineSection,
    ResearchOutline,
    WriterInvocation,
)
from app.application.dto.research import FormattedSource
from app.application.prompts.delivery import (
    build_outline_prompt,
    build_writer_prompt,
)
from app.domain.enums import FreshnessRequirement, OutputFormat
from app.domain.schemas import RequirementDetail


NOW = datetime(2026, 3, 16, 16, 30, tzinfo=UTC)


def build_requirement_detail() -> RequirementDetail:
    return RequirementDetail(
        research_goal="分析中国 AI 搜索产品的竞争格局与未来机会",
        domain="互联网 / AI 产品",
        requirement_details="偏商业报告，关注中国市场，覆盖近两年变化。",
        output_format=OutputFormat.BUSINESS_REPORT,
        freshness_requirement=FreshnessRequirement.HIGH,
        language="zh-CN",
    )


def build_sources() -> tuple[FormattedSource, ...]:
    return (
        FormattedSource(
            refer="ref_1",
            title="某公司发布会回顾",
            link="https://example.com/article-1",
            info="某产品在 2025 年发布企业版能力。",
        ),
        FormattedSource(
            refer="ref_2",
            title="行业分析报告",
            link="https://example.com/article-2",
            info="中国市场竞争正在加速。",
        ),
    )


def build_outline() -> ResearchOutline:
    return ResearchOutline(
        title="中国 AI 搜索产品竞争格局研究",
        sections=(
            OutlineSection(
                section_id="section_1",
                title="研究背景与问题定义",
                description="界定研究范围与市场背景。",
                order=1,
            ),
            OutlineSection(
                section_id="section_2",
                title="竞争格局与主要玩家",
                description="分析核心玩家与差异化能力。",
                order=2,
            ),
        ),
        entities=("AI 搜索产品", "中国市场", "竞争格局"),
    )


def test_outline_prompt_semantic_lock_keeps_role_and_output_constraints() -> None:
    prompt = build_outline_prompt(
        invocation=OutlineInvocation(
            prompt_name="outline_round",
            requirement_detail=build_requirement_detail(),
            formatted_sources=build_sources(),
            now=NOW,
        )
    )

    assert "你是一个深度研究架构师" in prompt.system_prompt
    assert "你**绝对不能**撰写具体内容" in prompt.system_prompt
    assert "章节描述内容**必须**满足以下要求" in prompt.system_prompt
    assert "\uff08\u5982 \u201c92%\u201d\uff09" in prompt.system_prompt
    assert '应使用\u201c选取代表性XX\u201d、\u201c对比主流XX\u201d等抽象化表述。' in prompt.system_prompt
    assert "**实体约束与大纲必须严格考量信息获取结果，保证已有信息可支撑**" in prompt.system_prompt
    assert '"标题"' in prompt.system_prompt
    assert '"section_1"' in prompt.system_prompt
    assert '"参考来源"' in prompt.system_prompt
    assert "2026-03-16T16:30:00+00:00" in prompt.system_prompt
    assert "<用户研究需求>" in prompt.user_prompt
    assert "分析中国 AI 搜索产品的竞争格局与未来机会" in prompt.user_prompt
    assert "ref_1" in prompt.user_prompt
    assert "某公司发布会回顾" in prompt.user_prompt


def test_writer_prompt_semantic_lock_keeps_markdown_tool_and_footnote_rules() -> None:
    prompt = build_writer_prompt(
        invocation=WriterInvocation(
            prompt_name="writer_round",
            requirement_detail=build_requirement_detail(),
            formatted_sources=build_sources(),
            outline=build_outline(),
            now=NOW,
        )
    )

    assert "\u4f60\u662f\u4e00\u4e2a\u8d44\u6df1\u7814\u7a76\u5458" in prompt.system_prompt
    assert "**\u4fdd\u8bc1\u7814\u7a76\u5185\u5bb9\u524d\u540e\u903b\u8f91\u8fde\u8d2f\u3001\u5408\u7406\u4e14\u6e05\u6670\u3001\u4e0a\u4e0b\u6587\u5b9e\u4f53\u4e00\u81f4\u65e0\u51b2\u7a81\u3002**" in prompt.system_prompt
    assert "**\uff01\u91cd\u8981\uff01\u7edd\u5bf9\u4e0d\u8981\u8d85\u8fc7\u4e00\u4e07\u5b57\uff01**" in prompt.system_prompt
    assert "\u6839\u636e\u5b9e\u9645\u4f7f\u7528\u7684\u53c2\u8003\u4fe1\u606f\u521b\u5efa\u811a\u6ce8\u53c2\u8003" in prompt.system_prompt
    assert "python_interpreter" in prompt.system_prompt
    assert "2026-03-16T16:30:00+00:00" in prompt.system_prompt
    assert "<参考信息>" in prompt.user_prompt
    assert "ref_1" in prompt.user_prompt
    assert "中国 AI 搜索产品竞争格局研究" in prompt.user_prompt
    assert "竞争格局与主要玩家" in prompt.user_prompt
