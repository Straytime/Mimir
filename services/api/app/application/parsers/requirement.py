import json
from json import JSONDecodeError
from typing import Any

from pydantic import ValidationError

from app.domain.schemas import RequirementDetail


class RequirementDetailParseError(Exception):
    pass


class RequirementDetailParser:
    def parse(self, raw_text: str) -> RequirementDetail:
        try:
            payload = json.loads(raw_text)
        except JSONDecodeError as exc:
            raise RequirementDetailParseError("Malformed requirement detail JSON.") from exc

        if not isinstance(payload, dict):
            raise RequirementDetailParseError("Requirement detail must be a JSON object.")

        try:
            return RequirementDetail.model_validate(
                {
                    **payload,
                    "raw_llm_output": payload,
                }
            )
        except ValidationError as exc:
            raise RequirementDetailParseError(
                "Requirement detail JSON did not match the schema."
            ) from exc
