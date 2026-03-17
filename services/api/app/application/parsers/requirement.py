import json
from json import JSONDecodeError
from typing import Any

from pydantic import ValidationError

from app.core.json_utils import strip_markdown_code_fence
from app.domain.schemas import RequirementDetail


class RequirementDetailParseError(Exception):
    pass


class RequirementDetailParser:
    def parse(self, raw_text: str) -> RequirementDetail:
        try:
            payload = json.loads(strip_markdown_code_fence(raw_text))
        except JSONDecodeError as exc:
            raise RequirementDetailParseError("Malformed requirement detail JSON.") from exc

        if not isinstance(payload, dict):
            raise RequirementDetailParseError("Requirement detail must be a JSON object.")

        try:
            normalized_payload = _normalize_requirement_payload(payload)
            return RequirementDetail.model_validate(
                {
                    **normalized_payload,
                    "raw_llm_output": payload,
                }
            )
        except ValidationError as exc:
            raise RequirementDetailParseError(
                "Requirement detail JSON did not match the schema."
            ) from exc


_OUTPUT_FORMAT_ALIASES = {
    "general": "general",
    "通用": "general",
    "research_report": "research_report",
    "研究报告": "research_report",
    "business_report": "business_report",
    "商业报告": "business_report",
    "academic_paper": "academic_paper",
    "专业论文": "academic_paper",
    "deep_article": "deep_article",
    "深度文章": "deep_article",
    "guide": "guide",
    "指南攻略": "guide",
    "shopping_recommendation": "shopping_recommendation",
    "购物推荐": "shopping_recommendation",
}

_FRESHNESS_REQUIREMENT_ALIASES = {
    "high": "high",
    "是": "high",
    "yes": "high",
    "normal": "normal",
    "否": "normal",
    "no": "normal",
}


def _normalize_requirement_payload(payload: dict[str, Any]) -> dict[str, Any]:
    requirement_details = _require_text(
        payload,
        "requirement_details",
        "需求明细",
    )
    return {
        "research_goal": _require_text(payload, "research_goal", "研究目标"),
        "domain": _require_text(payload, "domain", "所属垂域"),
        "requirement_details": requirement_details,
        "output_format": _normalize_output_format(
            _require_text(payload, "output_format", "适用形式")
        ),
        "freshness_requirement": _normalize_freshness_requirement(
            _require_text(payload, "freshness_requirement", "时效需求")
        ),
        "language": _normalize_language(
            _optional_text(payload, "language"),
            requirement_details=requirement_details,
        ),
    }


def _require_text(payload: dict[str, Any], *keys: str) -> str:
    value = _optional_text(payload, *keys)
    if value is None:
        raise RequirementDetailParseError(
            "Requirement detail JSON did not match the schema."
        )
    return value


def _optional_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_output_format(value: str) -> str:
    normalized = _OUTPUT_FORMAT_ALIASES.get(value.strip())
    if normalized is None:
        raise RequirementDetailParseError(
            "Requirement detail JSON did not match the schema."
        )
    return normalized


def _normalize_freshness_requirement(value: str) -> str:
    normalized = _FRESHNESS_REQUIREMENT_ALIASES.get(value.strip().lower())
    if normalized is not None:
        return normalized
    normalized = _FRESHNESS_REQUIREMENT_ALIASES.get(value.strip())
    if normalized is None:
        raise RequirementDetailParseError(
            "Requirement detail JSON did not match the schema."
        )
    return normalized


def _normalize_language(
    explicit_language: str | None,
    *,
    requirement_details: str,
) -> str:
    if explicit_language is not None:
        return explicit_language

    lowered = requirement_details.lower()
    if any(token in requirement_details for token in ("英文", "英语")) or any(
        token in lowered for token in ("english", "en-us", "en_us")
    ):
        return "en-US"
    return "zh-CN"
