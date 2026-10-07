import asyncio
import logging
from collections.abc import Sequence
from uuid import UUID

from app.core.auth_context import require_kp_president_user
from app.core.dates import local_to_utc, utc_now
from app.core.exceptions import (
    KpEventNotFound,
    MailCampaignLocked,
    MailCampaignNotFound,
    MailCampaignScheduleInPast,
    MailUnavailable,
)
from app.mail_templates.campaign import (
    CAMPAIGN_VARIABLES,
    campaign_identifier,
    render_campaign_mail,
    validate_campaign_texts,
)
from app.mail_templates.context import MAIL_CAMPAIGN_SAMPLE_CONTEXT
from app.mail_templates.renderer import RenderedMail
from app.mail_templates.texts import MailTemplateTexts
from app.models.kp_event import KpEvent
from app.models.mail import (
    EDITABLE_CAMPAIGN_STATUSES,
    MailCampaign,
    MailCampaignRecipient,
    MailCampaignRecipientStatus,
    MailCampaignStatus,
)
from app.models.user import User
from app.repositories.mail_campaign_repository import MailCampaignRepository
from app.schemas.mail import MailPreviewResult
from app.schemas.mail_campaign import (
    MailCampaignAudience,
    MailCampaignAudienceInput,
    MailCampaignAudienceResult,
    MailCampaignCompanyResult,
    MailCampaignCounts,
    MailCampaignInput,
    MailCampaignRecipientPreviewResult,
    MailCampaignRecipientResult,
    MailCampaignRenderInput,
    MailCampaignResult,
    MailCampaignScheduleInput,
    MailCampaignSummaryResult,
)
from app.services.auth_service import frontend_url
from app.services.mail_campaign_audience import (
    AudienceData,
    campaign_context,
    plan_recipients,
    recipient_address,
)
from app.services.mail_campaign_delivery import (
    LEASE,
    PLAIN_LOGIN_PATH,
    campaign_texts,
)
from app.services.mail_service import MailDeliveryFailed, MailService

logger = logging.getLogger(__name__)

COPY_SUFFIX = " (copy)"
UNKNOWN_EVENT = "-"
COUNTED_STATUSES = {
    MailCampaignRecipientStatus.PENDING: "pending",
    MailCampaignRecipientStatus.SENDING: "pending",
    MailCampaignRecipientStatus.SENT: "sent",
    MailCampaignRecipientStatus.FAILED: "failed",
    MailCampaignRecipientStatus.SKIPPED: "skipped",
}


def campaign_counts(counts: dict[str, int]) -> MailCampaignCounts:
    totals = {"pending": 0, "sent": 0, "failed": 0, "skipped": 0}
    for status, count in counts.items():
        key = COUNTED_STATUSES.get(MailCampaignRecipientStatus(status))
        if key is not None:
            totals[key] += count
    return MailCampaignCounts(**totals)


class MailCampaignService:
    def __init__(
        self,
        repository: MailCampaignRepository,
        mail_service: MailService,
        current_user: User,
    ) -> None:
        self.repository = repository
        self.mail_service = mail_service
        self.current_user = current_user

    def _authorize(self) -> None:
        require_kp_president_user(self.current_user)

    async def _event(self, event_id: UUID) -> KpEvent:
        event = await self.repository.get_event(event_id)
        if event is None:
            raise KpEventNotFound(f"mail_campaign_event:{event_id}")
        return event

    async def _campaign(self, campaign_id: UUID) -> MailCampaign:
        campaign = await self.repository.get(campaign_id)
        if campaign is None:
            raise MailCampaignNotFound(f"mail_campaign:{campaign_id}")
        return campaign

    async def _locked_editable(self, campaign_id: UUID) -> MailCampaign:
        campaign = await self.repository.lock(campaign_id)
        if campaign is None:
            await self.repository.rollback()
            raise MailCampaignNotFound(f"mail_campaign:{campaign_id}")
        status = campaign.status
        if status not in EDITABLE_CAMPAIGN_STATUSES:
            await self.repository.rollback()
            raise MailCampaignLocked(f"mail_campaign:{campaign_id}:{status}")
        return campaign

    async def _validate(
        self, texts: MailTemplateTexts, campaign_id: UUID | None
    ) -> None:
        await asyncio.to_thread(
            validate_campaign_texts, texts, campaign_identifier(campaign_id)
        )

    async def _summaries(
        self, campaigns: Sequence[MailCampaign]
    ) -> list[MailCampaignSummaryResult]:
        ids = [campaign.id for campaign in campaigns]
        counts = await self.repository.recipient_counts(ids)
        names = await self.repository.event_names(
            [campaign.event_id for campaign in campaigns]
        )
        return [
            MailCampaignSummaryResult(
                id=campaign.id,
                name=campaign.name,
                event_id=campaign.event_id,
                event_name=names.get(campaign.event_id, UNKNOWN_EVENT),
                status=MailCampaignStatus(campaign.status),
                scheduled_at=campaign.scheduled_at,
                started_at=campaign.started_at,
                finished_at=campaign.finished_at,
                created_at=campaign.created_at,
                updated_at=campaign.updated_at,
                counts=campaign_counts(counts.get(campaign.id, {})),
            )
            for campaign in campaigns
        ]

    async def _result(self, campaign: MailCampaign) -> MailCampaignResult:
        [summary] = await self._summaries([campaign])
        recipients = await self.repository.list_recipients(campaign.id)
        await self.repository.end_read_transaction()
        return MailCampaignResult(
            **summary.model_dump(),
            subject_de=campaign.subject_de,
            subject_en=campaign.subject_en,
            body_de=campaign.body_de,
            body_en=campaign.body_en,
            audience=MailCampaignAudience.model_validate(campaign.audience),
            recipients=[self._recipient(recipient) for recipient in recipients],
        )

    def _recipient(
        self, recipient: MailCampaignRecipient
    ) -> MailCampaignRecipientResult:
        return MailCampaignRecipientResult.model_validate(
            recipient, from_attributes=True
        )

    def _apply(self, campaign: MailCampaign, update: MailCampaignInput) -> None:
        campaign.name = update.name
        campaign.event_id = update.event_id
        campaign.subject_de = update.subject_de
        campaign.subject_en = update.subject_en
        campaign.body_de = update.body_de
        campaign.body_en = update.body_en
        campaign.audience = update.audience.model_dump(mode="json")
        campaign.updated_by_user_id = self.current_user.id

    async def list_campaigns(self) -> list[MailCampaignSummaryResult]:
        self._authorize()
        campaigns = await self.repository.list_campaigns()
        summaries = await self._summaries(campaigns)
        await self.repository.end_read_transaction()
        return summaries

    async def get_campaign(self, campaign_id: UUID) -> MailCampaignResult:
        self._authorize()
        return await self._result(await self._campaign(campaign_id))

    def variables(self) -> list[str]:
        self._authorize()
        return sorted(CAMPAIGN_VARIABLES)

    async def companies(self) -> list[MailCampaignCompanyResult]:
        self._authorize()
        companies = await self.repository.list_companies()
        await self.repository.end_read_transaction()
        return [
            MailCampaignCompanyResult(id=company.id, name=company.name)
            for company in companies
        ]

    async def create_campaign(self, create: MailCampaignInput) -> MailCampaignResult:
        self._authorize()
        await self._event(create.event_id)
        await self._validate(create.texts(), None)
        campaign = MailCampaign(
            name=create.name,
            event_id=create.event_id,
            subject_de=create.subject_de,
            body_de=create.body_de,
            created_by_user_id=self.current_user.id,
        )
        self._apply(campaign, create)
        campaign = await self.repository.save(campaign)
        logger.info("Mail campaign %s created by %s", campaign.id, self.current_user.id)
        return await self._result(campaign)

    async def update_campaign(
        self, campaign_id: UUID, update: MailCampaignInput
    ) -> MailCampaignResult:
        self._authorize()
        await self._event(update.event_id)
        await self._validate(update.texts(), campaign_id)
        campaign = await self._locked_editable(campaign_id)
        self._apply(campaign, update)
        campaign = await self.repository.save(campaign)
        logger.info("Mail campaign %s updated by %s", campaign.id, self.current_user.id)
        return await self._result(campaign)

    async def delete_campaign(self, campaign_id: UUID) -> None:
        self._authorize()
        campaign = await self._locked_editable(campaign_id)
        await self.repository.soft_delete(campaign)
        logger.info("Mail campaign %s deleted by %s", campaign_id, self.current_user.id)

    async def duplicate_campaign(self, campaign_id: UUID) -> MailCampaignResult:
        self._authorize()
        source = await self._campaign(campaign_id)
        copy = MailCampaign(
            name=f"{source.name}{COPY_SUFFIX}",
            event_id=source.event_id,
            subject_de=source.subject_de,
            subject_en=source.subject_en,
            body_de=source.body_de,
            body_en=source.body_en,
            audience=dict(source.audience),
            created_by_user_id=self.current_user.id,
            updated_by_user_id=self.current_user.id,
        )
        copy = await self.repository.save(copy)
        return await self._result(copy)

    async def _audience_data(self, event_id: UUID) -> AudienceData:
        return await self.repository.load_audience_data(await self._event(event_id))

    async def preview_audience(
        self, preview: MailCampaignAudienceInput
    ) -> MailCampaignAudienceResult:
        self._authorize()
        data = await self._audience_data(preview.event_id)
        planned = plan_recipients(preview.audience, data)
        recipients = [
            MailCampaignRecipientPreviewResult(
                company_id=entry.company.id,
                company_name=entry.company.name,
                email=entry.email,
                source=entry.source,
                skip_reason=entry.skip_reason,
                manually_included=entry.manually_included,
            )
            for entry in planned
        ]
        skipped = sum(1 for entry in planned if entry.skip_reason is not None)
        return MailCampaignAudienceResult(
            recipient_count=len(planned) - skipped,
            skipped_count=skipped,
            recipients=recipients,
        )

    async def _render(self, render: MailCampaignRenderInput) -> RenderedMail:
        data = await self._audience_data(render.event_id)
        company = data.company(render.company_id) if render.company_id else None
        if company is None:
            context = MAIL_CAMPAIGN_SAMPLE_CONTEXT
        else:
            _, source = recipient_address(company)
            context = campaign_context(
                data, company, source, frontend_url(PLAIN_LOGIN_PATH)
            )
        return await asyncio.to_thread(
            render_campaign_mail,
            render.texts(),
            context,
            campaign_identifier(None),
        )

    async def render_preview(
        self, render: MailCampaignRenderInput
    ) -> MailPreviewResult:
        self._authorize()
        rendered = await self._render(render)
        return MailPreviewResult(
            subject=rendered.subject, html=rendered.html, text=rendered.text
        )

    async def test_send(self, render: MailCampaignRenderInput) -> None:
        self._authorize()
        rendered = await self._render(render)
        message = self.mail_service.construct_mail(
            [self.current_user.email], rendered.subject, plain_text=rendered.text
        )
        if message is None:
            return
        try:
            await self.mail_service.send_mail(message)
        except MailDeliveryFailed as error:
            raise MailUnavailable(f"mail_campaign:test_send:{error}") from None
        logger.info("Mail campaign test sent to %s", self.current_user.id)

    async def send_now(self, campaign_id: UUID) -> MailCampaignResult:
        self._authorize()
        campaign = await self._campaign(campaign_id)
        await self._validate(campaign_texts(campaign), campaign.id)
        now = utc_now()
        started = await self.repository.transition(
            campaign_id,
            EDITABLE_CAMPAIGN_STATUSES,
            status=MailCampaignStatus.SENDING,
            started_at=now,
            lease_expires_at=now + LEASE,
            sent_by_user_id=self.current_user.id,
        )
        if not started:
            raise MailCampaignLocked(f"mail_campaign:{campaign_id}:send")
        logger.info("Mail campaign %s sent by %s", campaign_id, self.current_user.id)
        return await self._result(await self._campaign(campaign_id))

    async def schedule(
        self, campaign_id: UUID, schedule: MailCampaignScheduleInput
    ) -> MailCampaignResult:
        self._authorize()
        scheduled_at = local_to_utc(schedule.scheduled_at)
        if scheduled_at <= utc_now():
            raise MailCampaignScheduleInPast(f"mail_campaign:{campaign_id}:schedule")
        campaign = await self._locked_editable(campaign_id)
        await self._validate(campaign_texts(campaign), campaign.id)
        campaign.status = MailCampaignStatus.SCHEDULED
        campaign.scheduled_at = scheduled_at
        campaign.sent_by_user_id = self.current_user.id
        campaign = await self.repository.save(campaign)
        logger.info(
            "Mail campaign %s scheduled by %s", campaign_id, self.current_user.id
        )
        return await self._result(campaign)

    async def unschedule(self, campaign_id: UUID) -> MailCampaignResult:
        self._authorize()
        changed = await self.repository.transition(
            campaign_id,
            [MailCampaignStatus.SCHEDULED],
            status=MailCampaignStatus.DRAFT,
            scheduled_at=None,
        )
        if not changed:
            await self._campaign(campaign_id)
            raise MailCampaignLocked(f"mail_campaign:{campaign_id}:unschedule")
        return await self._result(await self._campaign(campaign_id))

    async def retry(self, campaign_id: UUID) -> MailCampaignResult:
        self._authorize()
        now = utc_now()
        changed = await self.repository.transition(
            campaign_id,
            [MailCampaignStatus.PARTIALLY_FAILED],
            status=MailCampaignStatus.SENDING,
            lease_expires_at=now + LEASE,
            finished_at=None,
        )
        if not changed:
            await self._campaign(campaign_id)
            raise MailCampaignLocked(f"mail_campaign:{campaign_id}:retry")
        await self.repository.reset_failed(campaign_id)
        logger.info("Mail campaign %s retried by %s", campaign_id, self.current_user.id)
        return await self._result(await self._campaign(campaign_id))
