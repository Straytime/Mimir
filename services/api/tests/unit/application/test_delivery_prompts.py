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
    assert "你绝对不能撰写具体内容" in prompt.system_prompt
    assert "实体约束与大纲必须严格考量信息获取结果" in prompt.system_prompt
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

    assert "你是一个资深研究员" in prompt.system_prompt
    assert "绝对不要超过一万字" in prompt.system_prompt
    assert "根据实际使用的参考信息创建脚注参考" in prompt.system_prompt
    assert "python_interpreter" in prompt.system_prompt
    assert "2026-03-16T16:30:00+00:00" in prompt.system_prompt
    assert "<参考信息>" in prompt.user_prompt
    assert "ref_1" in prompt.user_prompt
    assert "中国 AI 搜索产品竞争格局研究" in prompt.user_prompt
    assert "竞争格局与主要玩家" in prompt.user_prompt
