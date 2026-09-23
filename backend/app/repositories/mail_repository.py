from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.mail_templates.texts import MailTemplateTexts
from app.models.mail import MailTemplate
from app.repositories.base import BaseRepository


class MailTemplateRepository(BaseRepository[MailTemplate]):
    def __init__(self, session: AsyncSession):
        super().__init__(MailTemplate, session)

    async def get_by_key(self, key: str) -> MailTemplate | None:
        return await self._get_by_field(col(MailTemplate.key), key)

    async def list_templates(self) -> Sequence[MailTemplate]:
        statement = select(MailTemplate).order_by(col(MailTemplate.key))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def delete_by_key(self, key: str) -> None:
        template = await self.get_by_key(key)
        if template is None:
            return
        try:
            await self.hard_delete(template)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def upsert(
        self, key: str, texts: MailTemplateTexts, updated_by_user_id: UUID
    ) -> MailTemplate:
        try:
            template = await self.get_by_key(key) or MailTemplate(
                key=key,
                subject_de=texts.subject_de,
                subject_en=texts.subject_en,
                body_de=texts.body_de,
                body_en=texts.body_en,
            )
            template.subject_de = texts.subject_de
            template.subject_en = texts.subject_en
            template.body_de = texts.body_de
            template.body_en = texts.body_en
            template.updated_by_user_id = updated_by_user_id
            self.session.add(template)
            await self.session.commit()
            await self.session.refresh(template)
            return template
        except Exception as e:
            await self.session.rollback()
            raise e
