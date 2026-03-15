from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import AccessTokenResourceType


class TokenPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_expiry(self) -> "TokenPayloadModel":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")
        return self


class TaskTokenPayload(TokenPayloadModel):
    pass


class AccessTokenPayload(TokenPayloadModel):
    resource_type: AccessTokenResourceType
    resource_scope: str = Field(min_length=1)
