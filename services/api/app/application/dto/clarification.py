from typing import Annotated, Literal

from pydantic import Field

from app.application.dto.tasks import ApiDto
from app.domain.schemas import TaskSnapshot


class ClarificationOption(ApiDto):
    option_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class ClarificationQuestion(ApiDto):
    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    options: list[ClarificationOption] = Field(min_length=1)


class ClarificationQuestionSet(ApiDto):
    questions: list[ClarificationQuestion] = Field(min_length=1, max_length=5)


class ClarificationOptionAnswer(ApiDto):
    question_id: str = Field(min_length=1)
    selected_option_id: str = Field(min_length=1)
    selected_label: str = Field(min_length=1)


class NaturalClarificationSubmission(ApiDto):
    mode: Literal["natural"]
    answer_text: str = Field(min_length=1, max_length=500)


class OptionsClarificationSubmission(ApiDto):
    mode: Literal["options"]
    submitted_by_timeout: bool = False
    answers: list[ClarificationOptionAnswer] = Field(min_length=1)


ClarificationSubmission = Annotated[
    NaturalClarificationSubmission | OptionsClarificationSubmission,
    Field(discriminator="mode"),
]


class ClarificationAcceptedResponse(ApiDto):
    accepted: bool
    snapshot: TaskSnapshot
