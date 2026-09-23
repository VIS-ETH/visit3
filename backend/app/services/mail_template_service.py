from collections.abc import Sequence

from app.mail_templates.context import MailContext
from app.mail_templates.defaults import MAIL_TEMPLATE_DEFAULTS
from app.mail_templates.keys import MailTemplateKey
from app.mail_templates.renderer import RenderedMail, render_mail
from app.mail_templates.texts import MailTemplateTexts
from app.repositories.mail_repository import MailTemplateRepository
from app.services.mail_service import MailService
from app.services.notification_recipients import NotificationRecipients


def template_identifier(key: MailTemplateKey) -> str:
    return f"mail_template:{key}"


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
        return render_mail(await self.texts_for(key), context, template_identifier(key))

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
        if message is not None:
            await self.mail_service.send_mail(message)

    async def send_to_staff_notification(
        self, key: MailTemplateKey, context: MailContext
    ) -> None:
        recipient = await self.notification_recipients.staff_notification_email()
        await self.send(key, [recipient], context)
