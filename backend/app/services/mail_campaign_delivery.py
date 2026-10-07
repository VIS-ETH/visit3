import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dates import utc_now
from app.core.exceptions import MailTemplateInvalid
from app.mail_templates.campaign import campaign_identifier, render_campaign_mail
from app.mail_templates.texts import MailTemplateTexts
from app.models.mail import (
    MailCampaign,
    MailCampaignFailure,
    MailCampaignRecipient,
    MailCampaignRecipientSource,
    MailCampaignRecipientStatus,
    MailCampaignStatus,
)
from app.repositories.mail_campaign_repository import MailCampaignRepository
from app.repositories.token_repository import TokenRepository
from app.schemas.mail_campaign import MailCampaignAudience
from app.services.auth_service import LOGIN_LINK_PATH, frontend_url, safe_target_path
from app.services.mail_campaign_audience import (
    AudienceCompany,
    AudienceData,
    campaign_context,
    login_path,
    plan_recipients,
)
from app.services.mail_service import MailDeliveryFailed, MailService

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
Clock = Callable[[], datetime]

LEASE = timedelta(minutes=10)
MAX_CONSECUTIVE_FAILURES = 5
PLAIN_LOGIN_PATH = "/login"


def campaign_texts(campaign: MailCampaign) -> MailTemplateTexts:
    return MailTemplateTexts(
        subject_de=campaign.subject_de,
        subject_en=campaign.subject_en,
        body_de=campaign.body_de,
        body_en=campaign.body_en,
    )


def planned_rows(
    campaign_id: UUID, audience: MailCampaignAudience, data: AudienceData
) -> list[MailCampaignRecipient]:
    return [
        MailCampaignRecipient(
            campaign_id=campaign_id,
            company_id=planned.company.id,
            company_name=planned.company.name,
            email=planned.email,
            source=planned.source,
            contact_user_id=planned.company.contact.user_id
            if planned.company.contact is not None
            and planned.source == MailCampaignRecipientSource.CONTACT
            else None,
            status=MailCampaignRecipientStatus.SKIPPED
            if planned.skip_reason
            else MailCampaignRecipientStatus.PENDING,
            skip_reason=planned.skip_reason,
        )
        for planned in plan_recipients(audience, data)
    ]


class MailCampaignDelivery:
    def __init__(
        self,
        session_factory: SessionFactory,
        mail_service: MailService,
        *,
        pause_seconds: float,
        clock: Clock = utc_now,
    ) -> None:
        self.session_factory = session_factory
        self.mail_service = mail_service
        self.pause_seconds = pause_seconds
        self.clock = clock

    async def run_due(self) -> int:
        delivered = 0
        while True:
            async with self.session_factory() as session:
                now = self.clock()
                campaign_id = await MailCampaignRepository(session).claim_due(
                    now, now + LEASE
                )
            if campaign_id is None:
                return delivered
            await self.deliver(campaign_id)
            delivered += 1

    async def deliver_safely(self, campaign_id: UUID) -> None:
        try:
            await self.deliver(campaign_id)
        except Exception:
            logger.exception("Mail campaign %s delivery failed", campaign_id)

    async def deliver(self, campaign_id: UUID) -> None:
        async with self.session_factory() as session:
            repository = MailCampaignRepository(session)
            campaign = await repository.get(campaign_id)
            if campaign is None or campaign.status != MailCampaignStatus.SENDING:
                return
            event = await repository.get_event(campaign.event_id)
            data = await repository.load_audience_data(event) if event else None
            if campaign.recipients_resolved_at is None:
                audience = MailCampaignAudience.model_validate(campaign.audience)
                rows = planned_rows(campaign.id, audience, data) if data else []
                await repository.add_recipients(campaign.id, rows, self.clock())
            else:
                await repository.fail_interrupted(campaign.id)
            if data is None:
                await repository.abort_pending(campaign.id)
            else:
                await self._send_pending(session, repository, campaign, data)
            await self._finish(repository, campaign.id)

    async def _send_pending(
        self,
        session: AsyncSession,
        repository: MailCampaignRepository,
        campaign: MailCampaign,
        data: AudienceData,
    ) -> None:
        texts = campaign_texts(campaign)
        identifier = campaign_identifier(campaign.id)
        consecutive_failures = 0
        while (recipient := await repository.next_pending(campaign.id)) is not None:
            if not await repository.start_attempt(recipient.id, self.clock()):
                continue
            failure = await self._send_one(session, recipient, data, texts, identifier)
            await repository.finish_attempt(recipient.id, failure, self.clock())
            await repository.renew_lease(campaign.id, self.clock() + LEASE)
            consecutive_failures = consecutive_failures + 1 if failure else 0
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error(
                    "Mail campaign %s aborted after %s failed deliveries",
                    campaign.id,
                    consecutive_failures,
                )
                await repository.abort_pending(campaign.id)
                return
            if self.pause_seconds > 0:
                await asyncio.sleep(self.pause_seconds)

    def _company(
        self, recipient: MailCampaignRecipient, data: AudienceData
    ) -> AudienceCompany:
        return data.company(recipient.company_id) or AudienceCompany(
            id=recipient.company_id,
            name=recipient.company_name,
            contact=None,
            general_email=None,
        )

    def _source(
        self, recipient: MailCampaignRecipient, company: AudienceCompany
    ) -> MailCampaignRecipientSource | None:
        if recipient.source != MailCampaignRecipientSource.CONTACT:
            return MailCampaignRecipientSource.GENERAL_EMAIL
        if company.contact is None or company.contact.user_id != (
            recipient.contact_user_id
        ):
            return None
        return MailCampaignRecipientSource.CONTACT

    async def _login_url(
        self,
        session: AsyncSession,
        recipient: MailCampaignRecipient,
        data: AudienceData,
        source: MailCampaignRecipientSource | None,
    ) -> str:
        if source != MailCampaignRecipientSource.CONTACT or (
            recipient.contact_user_id is None
        ):
            return frontend_url(PLAIN_LOGIN_PATH)
        bookings = data.active_bookings().get(recipient.company_id, [])
        token = await TokenRepository(session).create_login_link_token(
            recipient.contact_user_id,
            safe_target_path(login_path(data.event.id, bookings)),
        )
        return frontend_url(f"{LOGIN_LINK_PATH}/{token}")

    async def _send_one(
        self,
        session: AsyncSession,
        recipient: MailCampaignRecipient,
        data: AudienceData,
        texts: MailTemplateTexts,
        identifier: str,
    ) -> MailCampaignFailure | None:
        company = self._company(recipient, data)
        source = self._source(recipient, company)
        login_url = await self._login_url(session, recipient, data, source)
        context = campaign_context(data, company, source, login_url)
        try:
            rendered = await asyncio.to_thread(
                render_campaign_mail, texts, context, identifier
            )
        except MailTemplateInvalid:
            logger.exception(
                "Mail campaign recipient %s could not render", recipient.id
            )
            return MailCampaignFailure.RENDER_FAILED
        message = self.mail_service.construct_mail(
            [str(recipient.email)], rendered.subject, plain_text=rendered.text
        )
        if message is None:
            return MailCampaignFailure.DELIVERY_FAILED
        try:
            await self.mail_service.send_mail(message)
        except MailDeliveryFailed as error:
            logger.warning("Mail campaign recipient %s failed: %s", recipient.id, error)
            return MailCampaignFailure.DELIVERY_FAILED
        return None

    async def _finish(
        self, repository: MailCampaignRepository, campaign_id: UUID
    ) -> None:
        failed = await repository.count_recipients(
            campaign_id, MailCampaignRecipientStatus.FAILED
        )
        status = (
            MailCampaignStatus.PARTIALLY_FAILED if failed else MailCampaignStatus.SENT
        )
        await repository.transition(
            campaign_id,
            [MailCampaignStatus.SENDING],
            status=status,
            finished_at=self.clock(),
            lease_expires_at=None,
        )
        logger.info("Mail campaign %s finished as %s", campaign_id, status)
