import asyncio
import logging
from datetime import datetime
from uuid import UUID

from app.core.auth_context import require_staff_user
from app.core.exceptions import MailTemplateNotFound
from app.mail_templates.context import SAMPLE_CONTEXTS, allowed_variables
from app.mail_templates.defaults import MAIL_TEMPLATE_DEFAULTS
from app.mail_templates.keys import MailTemplateKey
from app.mail_templates.texts import MailTemplateTexts
from app.models.mail import MailTemplate
from app.models.user import User
from app.repositories.mail_repository import MailTemplateRepository
from app.schemas.mail import (
    MailPreviewResult,
    MailTemplateResult,
    UpdateMailTemplateInput,
)
from app.services.mail_template_service import (
    MailTemplateService,
    texts_are_valid,
    validate_texts,
)

logger = logging.getLogger(__name__)


class MailTemplateAdminService:
    def __init__(
        self,
        mail_template_repository: MailTemplateRepository,
        mail_template_service: MailTemplateService,
        current_user: User,
    ) -> None:
        self.mail_template_repository = mail_template_repository
        self.mail_template_service = mail_template_service
        self.current_user = current_user

    def _known_key(self, key: str) -> MailTemplateKey:
        try:
            return MailTemplateKey(key)
        except ValueError:
            raise MailTemplateNotFound(f"mail_template:{key}")

    def _result(
        self,
        key: MailTemplateKey,
        texts: MailTemplateTexts,
        *,
        is_customized: bool,
        updated_at: datetime | None = None,
        updated_by_user_id: UUID | None = None,
    ) -> MailTemplateResult:
        defaults = MAIL_TEMPLATE_DEFAULTS[key]
        return MailTemplateResult(
            key=str(key),
            subject_de=texts.subject_de,
            subject_en=texts.subject_en,
            body_de=texts.body_de,
            body_en=texts.body_en,
            default_subject_de=defaults.subject_de,
            default_subject_en=defaults.subject_en,
            default_body_de=defaults.body_de,
            default_body_en=defaults.body_en,
            variables=sorted(allowed_variables(key)),
            is_customized=is_customized,
            is_valid=texts_are_valid(key, texts),
            updated_at=updated_at,
            updated_by_user_id=updated_by_user_id,
        )

    def _stored_result(
        self, key: MailTemplateKey, template: MailTemplate
    ) -> MailTemplateResult:
        return self._result(
            key,
            MailTemplateTexts(
                subject_de=template.subject_de,
                subject_en=template.subject_en,
                body_de=template.body_de,
                body_en=template.body_en,
            ),
            is_customized=True,
            updated_at=template.updated_at,
            updated_by_user_id=template.updated_by_user_id,
        )

    def _default_result(self, key: MailTemplateKey) -> MailTemplateResult:
        return self._result(key, MAIL_TEMPLATE_DEFAULTS[key], is_customized=False)

    async def list_templates(self) -> list[MailTemplateResult]:
        require_staff_user(self.current_user)
        stored = {
            template.key: template
            for template in await self.mail_template_repository.list_templates()
        }
        return [
            self._stored_result(key, stored[str(key)])
            if str(key) in stored
            else self._default_result(key)
            for key in MailTemplateKey
        ]

    async def get_template(self, key: str) -> MailTemplateResult:
        require_staff_user(self.current_user)
        known_key = self._known_key(key)
        template = await self.mail_template_repository.get_by_key(str(known_key))
        if template is None:
            return self._default_result(known_key)
        return self._stored_result(known_key, template)

    def _validated_texts(
        self, key: MailTemplateKey, update: UpdateMailTemplateInput
    ) -> MailTemplateTexts:
        texts = MailTemplateTexts(
            subject_de=update.subject_de,
            subject_en=update.subject_en,
            body_de=update.body_de,
            body_en=update.body_en,
        )
        validate_texts(key, texts)
        return texts

    async def update_template(
        self, key: str, update: UpdateMailTemplateInput
    ) -> MailTemplateResult:
        require_staff_user(self.current_user)
        known_key = self._known_key(key)
        texts = await asyncio.to_thread(self._validated_texts, known_key, update)
        template = await self.mail_template_repository.upsert(
            str(known_key), texts, self.current_user.id
        )
        logger.info("Mail template updated by %s: %s", self.current_user.id, known_key)
        return self._stored_result(known_key, template)

    async def reset_template(self, key: str) -> MailTemplateResult:
        require_staff_user(self.current_user)
        known_key = self._known_key(key)
        await self.mail_template_repository.delete_by_key(str(known_key))
        logger.info("Mail template reset by %s: %s", self.current_user.id, known_key)
        return self._default_result(known_key)

    async def preview(self, key: str) -> MailPreviewResult:
        require_staff_user(self.current_user)
        known_key = self._known_key(key)
        rendered = await self.mail_template_service.render(
            known_key, SAMPLE_CONTEXTS[known_key]
        )
        return MailPreviewResult(
            subject=rendered.subject, html=rendered.html, text=rendered.text
        )

    async def test_send(self, key: str) -> None:
        require_staff_user(self.current_user)
        known_key = self._known_key(key)
        await self.mail_template_service.send(
            known_key, [self.current_user.email], SAMPLE_CONTEXTS[known_key]
        )
        logger.info(
            "Mail template test sent to %s: %s", self.current_user.id, known_key
        )
