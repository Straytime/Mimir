"""Unit tests for _strip_markdown_preamble helper."""
from app.application.services.delivery import _strip_markdown_preamble


def test_strips_preamble_before_first_h1() -> None:
    md = "好的，以下是报告：\n\n# 研究报告\n\n正文内容"
    assert _strip_markdown_preamble(md) == "# 研究报告\n\n正文内容"


def test_no_preamble_returns_unchanged() -> None:
    md = "# 研究报告\n\n正文内容"
    assert _strip_markdown_preamble(md) == "# 研究报告\n\n正文内容"


def test_no_h1_returns_unchanged() -> None:
    md = "## 二级标题\n\n正文内容"
    assert _strip_markdown_preamble(md) == "## 二级标题\n\n正文内容"


def test_multiple_h1_strips_to_first() -> None:
    md = "声明文本\n\n# 第一章\n\n内容\n\n# 第二章\n\n内容"
    assert _strip_markdown_preamble(md) == "# 第一章\n\n内容\n\n# 第二章\n\n内容"


def test_empty_string_returns_empty() -> None:
    assert _strip_markdown_preamble("") == ""


def test_h2_before_h1_not_treated_as_cut_point() -> None:
    md = "说明\n\n## 附注\n\n# 正式报告\n\n内容"
    assert _strip_markdown_preamble(md) == "# 正式报告\n\n内容"
