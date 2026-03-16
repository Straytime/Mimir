from datetime import datetime


def build_natural_clarification_prompt(
    *,
    initial_query: str,
    client_timezone: str,
    client_locale: str,
    now: datetime,
) -> str:
    return f"""
你是 Mimir 后端的澄清问题生成器。
当前时间: {now.isoformat()}
用户时区: {client_timezone}
用户语言: {client_locale}
原始需求: {initial_query}

请基于以上信息，只输出面向用户的自然语言澄清问题。
要求：
- 只输出 1 个简洁问题
- 不要输出 JSON
- 不要输出 Markdown 代码块
- 不要附带解释、编号或系统说明
""".strip()


def build_options_clarification_prompt(
    *,
    initial_query: str,
    client_timezone: str,
    client_locale: str,
    now: datetime,
) -> str:
    return f"""
你是 Mimir 后端的结构化澄清问题生成器。
当前时间: {now.isoformat()}
用户时区: {client_timezone}
用户语言: {client_locale}
原始需求: {initial_query}

请输出 1 到 5 个问题，每个问题附带若干可选项。
要求：
- 只输出问题和选项正文
- 问题必须适合前端直接渲染
- 不要生成 o_auto，后端会统一追加
- 不要输出 JSON
- 不要输出 Markdown 代码块
""".strip()
