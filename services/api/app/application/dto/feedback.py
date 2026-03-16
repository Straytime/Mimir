from pydantic import Field

from app.application.dto.tasks import ApiDto
from app.domain.schemas import RequirementDetail


class FeedbackSubmission(ApiDto):
    feedback_text: str = Field(min_length=1, max_length=1000)


class FeedbackAcceptedResponse(ApiDto):
    accepted: bool
    revision_id: str
    revision_number: int = Field(ge=1)


class FeedbackAnalysisInput(ApiDto):
    initial_query: str = Field(min_length=1)
    previous_requirement_detail: RequirementDetail
    feedback_text: str = Field(min_length=1, max_length=1000)
