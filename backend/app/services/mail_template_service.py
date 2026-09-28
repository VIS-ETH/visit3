import asyncio
import logging
from collections.abc import Sequence

from app.core.exceptions import MailTemplateInvalid, MailUnavailable
from app.core.request_id import current_request_id
from app.mail_templates.context import SAMPLE_CONTEXTS, MailContext, allowed_variables
from app.mail_templates.defaults import MAIL_TEMPLATE_DEFAULTS
from app.mail_templates.keys import MailTemplateKey
from app.mail_templates.renderer import (
    RenderedMail,
    render_fragment,
    render_mail,
    unknown_variables,
)
from app.mail_templates.texts import MailTemplateTexts
from app.repositories.mail_repository import MailTemplateRepository
from app.services.mail_service import MailDeliveryFailed, MailService
from app.services.notification_recipients import NotificationRecipients

logger = logging.getLogger(__name__)


def template_identifier(key: MailTemplateKey) -> str:
    return f"mail_template:{key}"


def validate_texts(key: MailTemplateKey, texts: MailTemplateTexts) -> None:
    identifier = template_identifier(key)
    allowed = allowed_variables(key)
    sample = SAMPLE_CONTEXTS[key].variables()
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


def texts_are_valid(key: MailTemplateKey, texts: MailTemplateTexts) -> bool:
    try:
        validate_texts(key, texts)
    except MailTemplateInvalid:
        return False
    return True


class MailTemplateService:
    def __init__(
        self,
        mail_template_repository: MailTemplateRepository,
        notification_recipients: NotificationRecipients,
        mail_service: MailService,
    ) -> None:
        self.mail_template_repository = mail_template_repository
        self.notification_recipients = notification_recipients
        self.mail_service = mail_service

    async def texts_for(self, key: MailTemplateKey) -> MailTemplateTexts:
        template = await self.mail_template_repository.get_by_key(str(key))
        if template is None:
            return MAIL_TEMPLATE_DEFAULTS[key]
        return MailTemplateTexts(
            subject_de=template.subject_de,
            subject_en=template.subject_en,
            body_de=template.body_de,
            body_en=template.body_en,
        )

    async def render(self, key: MailTemplateKey, context: MailContext) -> RenderedMail:
        texts = await self.texts_for(key)
        identifier = template_identifier(key)
        try:
            return await asyncio.to_thread(render_mail, texts, context, identifier)
        except MailTemplateInvalid as error:
            if texts == MAIL_TEMPLATE_DEFAULTS[key]:
                raise
            logger.error(
                "Stored mail template %s is invalid, sending the default "
                "(request %s): %r",
                key,
                current_request_id(),
                error.message,
            )
        return await asyncio.to_thread(
            render_mail, MAIL_TEMPLATE_DEFAULTS[key], context, identifier
        )

    async def send(
        self, key: MailTemplateKey, recipients: Sequence[str], context: MailContext
    ) -> None:
        if not recipients:
            return
        rendered = await self.render(key, context)
        # The notifications API rejects multipart bodies ("multipart mail not
        # supported"), so only the plain-text rendering can be delivered.
        message = self.mail_service.construct_mail(
            recipients, rendered.subject, plain_text=rendered.text
        )
        if message is None:
            return
        try:
            await self.mail_service.send_mail(message)
        except MailDeliveryFailed as error:
            raise MailUnavailable(f"{template_identifier(key)}:{error}") from None

    async def send_to_staff_notification(
        self, key: MailTemplateKey, context: MailContext
    ) -> None:
        recipient = await self.notification_recipients.staff_notification_email()
        await self.send(key, [recipient], context)
