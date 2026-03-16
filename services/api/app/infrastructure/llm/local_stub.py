from app.application.services.llm import TextGeneration


class LocalStubClarificationGenerator:
    async def generate_natural(self, prompt: str) -> TextGeneration:
        return TextGeneration(
            deltas=("为了更好开展研究，请补充你最关心的研究重点。",),
            full_text="为了更好开展研究，请补充你最关心的研究重点。",
        )

    async def generate_options(self, prompt: str) -> TextGeneration:
        return TextGeneration(
            deltas=("1. 你更想聚焦哪个方向？\nA. 行业现状\nB. 竞争格局",),
            full_text="1. 你更想聚焦哪个方向？\nA. 行业现状\nB. 竞争格局",
        )


class LocalStubRequirementAnalyzer:
    async def analyze(self, prompt: str) -> TextGeneration:
        return TextGeneration(
            deltas=(
                '{\n  "research_goal": "分析中国 AI 搜索产品竞争格局",',
            ),
            full_text="""
            {
              "research_goal": "分析中国 AI 搜索产品竞争格局",
              "domain": "互联网 / AI 产品",
              "requirement_details": "聚焦中国市场，偏商业分析，覆盖近两年变化。",
              "output_format": "business_report",
              "freshness_requirement": "high",
              "language": "zh-CN"
            }
            """,
        )


class LocalStubFeedbackAnalyzer:
    async def analyze(self, prompt: str) -> TextGeneration:
        return TextGeneration(
            deltas=(
                '{\n  "research_goal": "补充 B 端落地分析",',
            ),
            full_text="""
            {
              "research_goal": "补充 B 端落地分析",
              "domain": "互联网 / AI 产品",
              "requirement_details": "补充比较各家产品在 B 端场景的落地情况，并删掉不确定推测。",
              "output_format": "business_report",
              "freshness_requirement": "high",
              "language": "zh-CN"
            }
            """,
        )
