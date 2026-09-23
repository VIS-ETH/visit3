from uuid import UUID

from sqlmodel import Field

from app.models.base import BaseEntity


class MailTemplate(BaseEntity, table=True):
    key: str = Field(index=True, unique=True)
    subject_de: str
    subject_en: str
    body_de: str
    body_en: str
    updated_by_user_id: UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
