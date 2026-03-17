import pytest

from app.application.parsers.clarification import (
    ClarificationOptionsParseError,
    ClarificationOptionsParser,
)
from app.application.parsers.requirement import (
    RequirementDetailParseError,
    RequirementDetailParser,
)


def test_options_parser_extracts_structured_questions_from_loose_llm_output() -> None:
    parser = ClarificationOptionsParser()

    question_set = parser.parse(
        """
        1. 这次研究更偏向哪个方向？
        A. 行业现状与趋势
        B. 主要参与者与格局
        C. 商业机会与风险

        Q2: 你更看重哪类输出？
        - 商业分析
        - 产品策略建议
        """
    )

    assert question_set.model_dump(mode="json") == {
        "questions": [
            {
                "question_id": "q_1",
                "question": "这次研究更偏向哪个方向？",
                "options": [
                    {"option_id": "o_1", "label": "行业现状与趋势"},
                    {"option_id": "o_2", "label": "主要参与者与格局"},
                    {"option_id": "o_3", "label": "商业机会与风险"},
                    {"option_id": "o_auto", "label": "自动"},
                ],
            },
            {
                "question_id": "q_2",
                "question": "你更看重哪类输出？",
                "options": [
                    {"option_id": "o_1", "label": "商业分析"},
                    {"option_id": "o_2", "label": "产品策略建议"},
                    {"option_id": "o_auto", "label": "自动"},
                ],
            },
        ]
    }


def test_options_parser_truncates_to_five_questions() -> None:
    parser = ClarificationOptionsParser()

    question_set = parser.parse(
        """
        1. Q1?
        A. A1
        2. Q2?
        A. A2
        3. Q3?
        A. A3
        4. Q4?
        A. A4
        5. Q5?
        A. A5
        6. Q6?
        A. A6
        """
    )

    assert len(question_set.questions) == 5
    assert [question.question_id for question in question_set.questions] == [
        "q_1",
        "q_2",
        "q_3",
        "q_4",
        "q_5",
    ]


def test_options_parser_skips_questions_without_options() -> None:
    parser = ClarificationOptionsParser()

    question_set = parser.parse(
        """
        1. 需要聚焦哪个市场？
        这里没有选项

        2. 更偏向哪类产出？
        A. 商业报告
        B. 产品分析
        """
    )

    assert len(question_set.questions) == 1
    assert question_set.questions[0].question == "更偏向哪类产出？"


def test_options_parser_tolerates_irregular_option_markers_and_noise_between_questions() -> None:
    parser = ClarificationOptionsParser()

    question_set = parser.parse(
        """
        说明：以下是澄清问题草稿。

        问题 1：你最关注哪部分？
        option a: 竞争格局
        option b: 商业机会

        这行是无关说明，应被忽略。

        问题 2：需要覆盖哪些地区？
        ① 中国
        ② 海外
        """
    )

    assert [question.question for question in question_set.questions] == [
        "你最关注哪部分？",
        "需要覆盖哪些地区？",
    ]
    assert [option.label for option in question_set.questions[1].options] == [
        "中国",
        "海外",
        "自动",
    ]


def test_options_parser_raises_explicit_error_when_no_valid_question_can_be_built() -> None:
    parser = ClarificationOptionsParser()

    with pytest.raises(ClarificationOptionsParseError):
        parser.parse("这是一段完全无法解析成问题和选项的内容。")


def test_requirement_detail_parser_maps_valid_json_into_schema() -> None:
    parser = RequirementDetailParser()

    detail = parser.parse(
        """
        {
          "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
          "domain": "互联网 / AI 产品",
          "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化。",
          "output_format": "business_report",
          "freshness_requirement": "high",
          "language": "zh-CN"
        }
        """
    )

    assert detail.model_dump(mode="json", exclude_none=True) == {
        "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
        "domain": "互联网 / AI 产品",
        "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化。",
        "output_format": "business_report",
        "freshness_requirement": "high",
        "language": "zh-CN",
        "raw_llm_output": {
            "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
            "domain": "互联网 / AI 产品",
            "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化。",
            "output_format": "business_report",
            "freshness_requirement": "high",
            "language": "zh-CN",
        },
    }


def test_requirement_detail_parser_accepts_fenced_prd_json_and_normalizes_keys() -> None:
    parser = RequirementDetailParser()

    detail = parser.parse(
        """
        ```json
        {
          "研究目标": "分析中国 AI 搜索产品的竞争格局与机会",
          "所属垂域": "互联网 / AI 产品",
          "需求明细": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
          "适用形式": "商业报告",
          "时效需求": "是"
        }
        ```
        """
    )

    assert detail.model_dump(mode="json", exclude_none=True) == {
        "research_goal": "分析中国 AI 搜索产品的竞争格局与机会",
        "domain": "互联网 / AI 产品",
        "requirement_details": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
        "output_format": "business_report",
        "freshness_requirement": "high",
        "language": "zh-CN",
        "raw_llm_output": {
            "研究目标": "分析中国 AI 搜索产品的竞争格局与机会",
            "所属垂域": "互联网 / AI 产品",
            "需求明细": "偏商业报告，关注中国市场，重点覆盖近两年变化，输出语言为中文。",
            "适用形式": "商业报告",
            "时效需求": "是",
        },
    }


def test_feedback_requirement_detail_parser_accepts_fenced_prd_json() -> None:
    parser = RequirementDetailParser()

    detail = parser.parse(
        """
        ```json
        {
          "研究目标": "补充中国 AI 搜索产品 B 端场景竞争格局",
          "所属垂域": "互联网 / AI 产品",
          "需求明细": "保留中文输出，增加 B 端落地案例，删除不确定推测。",
          "适用形式": "商业报告",
          "时效需求": "否"
        }
        ```
        """
    )

    assert detail.research_goal == "补充中国 AI 搜索产品 B 端场景竞争格局"
    assert detail.output_format == "business_report"
    assert detail.freshness_requirement == "normal"
    assert detail.language == "zh-CN"


def test_requirement_detail_parser_rejects_malformed_json_with_explicit_error() -> None:
    parser = RequirementDetailParser()

    with pytest.raises(RequirementDetailParseError):
        parser.parse('{"research_goal": "缺了结尾"')


def test_requirement_detail_parser_still_rejects_non_json_noise_wrapped_output() -> None:
    parser = RequirementDetailParser()

    with pytest.raises(RequirementDetailParseError):
        parser.parse(
            """
            下面是结果：
            ```json
            {"研究目标":"有包装噪音"}
            ```
            """
        )
