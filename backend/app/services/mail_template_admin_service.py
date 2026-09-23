import logging
from datetime import datetime
from uuid import UUID

from app.core.auth_context import require_staff_user
from app.core.exceptions import MailTemplateInvalid, MailTemplateNotFound
from app.mail_templates.context import SAMPLE_CONTEXTS, allowed_variables
from app.mail_templates.defaults import MAIL_TEMPLATE_DEFAULTS
from app.mail_templates.keys import MailTemplateKey
from app.mail_templates.renderer import render_fragment, unknown_variables
from app.mail_templates.texts import MailTemplateTexts
from app.models.mail import MailTemplate
from app.models.user import User
from app.repositories.mail_repository import MailTemplateRepository
from app.schemas.mail import (
    MailPreviewResult,
    MailTemplateResult,
    UpdateMailTemplateInput,
)
from app.services.mail_template_service import MailTemplateService, template_identifier

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
        identifier = template_identifier(key)
        allowed = allowed_variables(key)
        sample = SAMPLE_CONTEXTS[key].variables()
        texts = MailTemplateTexts(
            subject_de=update.subject_de,
            subject_en=update.subject_en,
            body_de=update.body_de,
            body_en=update.body_en,
        )
        for field, source in (
            ("subject_de", texts.subject_de),
            ("subject_en", texts.subject_en),
            ("body_de", texts.body_de),
            ("body_en", texts.body_en),
        ):
            unknown = sorted(unknown_variables(source, allowed, identifier, field))
            if unknown:
                raise MailTemplateInvalid(
                    identifier,
                    f"unknown variable '{unknown[0]}' in {field}",
                    field,
                    unknown[0],
                )
            render_fragment(source, sample, identifier, field)
        return texts

    async def update_template(
        self, key: str, update: UpdateMailTemplateInput
    ) -> MailTemplateResult:
        require_staff_user(self.current_user)
        known_key = self._known_key(key)
        texts = self._validated_texts(known_key, update)
        template = await self.mail_template_repository.upsert(
            str(known_key), texts, self.current_user.id
        )
        logger.info(f"Mail template updated by {self.current_user.email}: {known_key}")
        return self._stored_result(known_key, template)

    async def reset_template(self, key: str) -> MailTemplateResult:
        require_staff_user(self.current_user)
        known_key = self._known_key(key)
        await self.mail_template_repository.delete_by_key(str(known_key))
        logger.info(f"Mail template reset by {self.current_user.email}: {known_key}")
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
            f"Mail template test sent to {self.current_user.email}: {known_key}"
        )
