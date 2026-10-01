from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, Select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, select, update

from app.core.deleted_filter import include_deleted_for
from app.models.company import Company, KpCompanyProfile
from app.models.kp_event import KpEvent, KpEventBooking, KpEventBoothZone
from app.models.mail import (
    MailCampaign,
    MailCampaignFailure,
    MailCampaignRecipient,
    MailCampaignRecipientStatus,
    MailCampaignStatus,
)
from app.repositories.base import BaseRepository, rel
from app.services.mail_campaign_audience import (
    AudienceBooking,
    AudienceCompany,
    AudienceData,
    AudienceEvent,
    eligible_contact,
)


def _changed(result: object) -> bool:
    return cast(CursorResult[Any], result).rowcount == 1


class MailCampaignRepository(BaseRepository[MailCampaign]):
    def __init__(self, session: AsyncSession):
        super().__init__(MailCampaign, session)

    async def list_campaigns(self) -> Sequence[MailCampaign]:
        statement = select(MailCampaign).order_by(col(MailCampaign.created_at).desc())
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def event_names(self, event_ids: Sequence[UUID]) -> dict[UUID, str]:
        if not event_ids:
            return {}
        statement = include_deleted_for(
            select(KpEvent).where(col(KpEvent.id).in_(set(event_ids)))
        )
        result = await self.session.execute(statement)
        return {event.id: event.name for event in result.scalars().all()}

    async def get_event(self, event_id: UUID) -> KpEvent | None:
        statement = select(KpEvent).where(col(KpEvent.id) == event_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def recipient_counts(
        self, campaign_ids: Sequence[UUID]
    ) -> dict[UUID, dict[str, int]]:
        counts: dict[UUID, dict[str, int]] = defaultdict(dict)
        if not campaign_ids:
            return counts
        statement = (
            select(
                col(MailCampaignRecipient.campaign_id),
                col(MailCampaignRecipient.status),
                func.count(col(MailCampaignRecipient.id)),
            )
            .where(col(MailCampaignRecipient.campaign_id).in_(set(campaign_ids)))
            .group_by(
                col(MailCampaignRecipient.campaign_id),
                col(MailCampaignRecipient.status),
            )
        )
        result = await self.session.execute(statement)
        for campaign_id, status, count in result.all():
            counts[campaign_id][status] = count
        return counts

    async def get(self, campaign_id: UUID) -> MailCampaign | None:
        statement = (
            select(MailCampaign)
            .where(col(MailCampaign.id) == campaign_id)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    def locked_campaign_statement(campaign_id: UUID) -> Select[tuple[MailCampaign]]:
        return (
            select(MailCampaign)
            .where(col(MailCampaign.id) == campaign_id)
            .with_for_update(of=MailCampaign)
            .execution_options(populate_existing=True)
        )

    async def lock(self, campaign_id: UUID) -> MailCampaign | None:
        result = await self.session.execute(self.locked_campaign_statement(campaign_id))
        return result.scalar_one_or_none()

    async def save(self, campaign: MailCampaign) -> MailCampaign:
        try:
            self.session.add(campaign)
            await self.session.commit()
            await self.session.refresh(campaign)
            return campaign
        except Exception as e:
            await self.session.rollback()
            raise e

    async def soft_delete(self, campaign: MailCampaign) -> None:
        try:
            self.delete(campaign)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e

    async def rollback(self) -> None:
        await self.session.rollback()

    async def transition(
        self,
        campaign_id: UUID,
        from_statuses: Sequence[MailCampaignStatus],
        **values: Any,
    ) -> bool:
        statement = (
            update(MailCampaign)
            .where(
                col(MailCampaign.id) == campaign_id,
                col(MailCampaign.status).in_(from_statuses),
                self._not_deleted(MailCampaign),
            )
            .values(**values)
        )
        changed = _changed(await self.session.execute(statement))
        await self.session.commit()
        return changed

    @staticmethod
    def _due(now: datetime) -> ColumnElement[bool]:
        return and_(
            col(MailCampaign.deleted_at).is_(None),
            or_(
                and_(
                    col(MailCampaign.status) == MailCampaignStatus.SCHEDULED,
                    col(MailCampaign.scheduled_at) <= now,
                ),
                and_(
                    col(MailCampaign.status) == MailCampaignStatus.SENDING,
                    col(MailCampaign.lease_expires_at) < now,
                ),
            ),
        )

    @staticmethod
    def due_campaign_statement(now: datetime) -> Select[tuple[UUID]]:
        return (
            select(col(MailCampaign.id))
            .where(MailCampaignRepository._due(now))
            .order_by(col(MailCampaign.scheduled_at).asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

    async def claim_due(self, now: datetime, lease_until: datetime) -> UUID | None:
        result = await self.session.execute(self.due_campaign_statement(now))
        campaign_id = result.scalar_one_or_none()
        if campaign_id is None:
            await self.session.commit()
            return None
        statement = (
            update(MailCampaign)
            .where(col(MailCampaign.id) == campaign_id, self._due(now))
            .values(
                status=MailCampaignStatus.SENDING,
                lease_expires_at=lease_until,
                started_at=func.coalesce(col(MailCampaign.started_at), now),
            )
        )
        claimed = _changed(await self.session.execute(statement))
        await self.session.commit()
        return campaign_id if claimed else None

    async def renew_lease(self, campaign_id: UUID, lease_until: datetime) -> None:
        statement = (
            update(MailCampaign)
            .where(
                col(MailCampaign.id) == campaign_id,
                col(MailCampaign.status) == MailCampaignStatus.SENDING,
            )
            .values(lease_expires_at=lease_until)
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def list_recipients(
        self, campaign_id: UUID
    ) -> Sequence[MailCampaignRecipient]:
        statement = (
            select(MailCampaignRecipient)
            .where(col(MailCampaignRecipient.campaign_id) == campaign_id)
            .order_by(
                func.lower(col(MailCampaignRecipient.company_name)),
                col(MailCampaignRecipient.id),
            )
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def add_recipients(
        self,
        campaign_id: UUID,
        recipients: Sequence[MailCampaignRecipient],
        now: datetime,
    ) -> bool:
        try:
            statement = (
                update(MailCampaign)
                .where(
                    col(MailCampaign.id) == campaign_id,
                    col(MailCampaign.recipients_resolved_at).is_(None),
                )
                .values(recipients_resolved_at=now)
            )
            if not _changed(await self.session.execute(statement)):
                await self.session.rollback()
                return False
            self.session.add_all(recipients)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            raise e

    async def next_pending(self, campaign_id: UUID) -> MailCampaignRecipient | None:
        statement = (
            select(MailCampaignRecipient)
            .where(
                col(MailCampaignRecipient.campaign_id) == campaign_id,
                col(MailCampaignRecipient.status)
                == MailCampaignRecipientStatus.PENDING,
            )
            .order_by(
                func.lower(col(MailCampaignRecipient.company_name)),
                col(MailCampaignRecipient.id),
            )
            .limit(1)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(statement)
        recipient = result.scalar_one_or_none()
        await self.session.commit()
        return recipient

    async def _set_recipients(
        self,
        *conditions: ColumnElement[bool],
        **values: Any,
    ) -> bool:
        statement = update(MailCampaignRecipient).where(*conditions).values(**values)
        changed = _changed(await self.session.execute(statement))
        await self.session.commit()
        return changed

    async def start_attempt(self, recipient_id: UUID, now: datetime) -> bool:
        return await self._set_recipients(
            col(MailCampaignRecipient.id) == recipient_id,
            col(MailCampaignRecipient.status) == MailCampaignRecipientStatus.PENDING,
            status=MailCampaignRecipientStatus.SENDING,
            attempts=col(MailCampaignRecipient.attempts) + 1,
            last_attempt_at=now,
            error=None,
        )

    async def finish_attempt(
        self,
        recipient_id: UUID,
        failure: MailCampaignFailure | None,
        now: datetime,
    ) -> None:
        await self._set_recipients(
            col(MailCampaignRecipient.id) == recipient_id,
            col(MailCampaignRecipient.status) == MailCampaignRecipientStatus.SENDING,
            status=MailCampaignRecipientStatus.FAILED
            if failure
            else MailCampaignRecipientStatus.SENT,
            error=failure,
            sent_at=None if failure else now,
        )

    async def _move_recipients(
        self,
        campaign_id: UUID,
        source: MailCampaignRecipientStatus,
        target: MailCampaignRecipientStatus,
        error: MailCampaignFailure | None,
    ) -> None:
        await self._set_recipients(
            col(MailCampaignRecipient.campaign_id) == campaign_id,
            col(MailCampaignRecipient.status) == source,
            status=target,
            error=error,
        )

    async def fail_interrupted(self, campaign_id: UUID) -> None:
        await self._move_recipients(
            campaign_id,
            MailCampaignRecipientStatus.SENDING,
            MailCampaignRecipientStatus.FAILED,
            MailCampaignFailure.INTERRUPTED,
        )

    async def abort_pending(self, campaign_id: UUID) -> None:
        await self._move_recipients(
            campaign_id,
            MailCampaignRecipientStatus.PENDING,
            MailCampaignRecipientStatus.FAILED,
            MailCampaignFailure.ABORTED,
        )

    async def reset_failed(self, campaign_id: UUID) -> None:
        await self._move_recipients(
            campaign_id,
            MailCampaignRecipientStatus.FAILED,
            MailCampaignRecipientStatus.PENDING,
            None,
        )

    async def count_recipients(
        self, campaign_id: UUID, status: MailCampaignRecipientStatus
    ) -> int:
        statement = select(func.count(col(MailCampaignRecipient.id))).where(
            col(MailCampaignRecipient.campaign_id) == campaign_id,
            col(MailCampaignRecipient.status) == status,
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def list_companies(self) -> Sequence[Company]:
        statement = select(Company).order_by(func.lower(col(Company.name)))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def load_audience_data(self, event: KpEvent) -> AudienceData:
        companies_statement = (
            select(Company)
            .options(
                selectinload(rel(Company.kp_profile)).selectinload(
                    rel(KpCompanyProfile.kp_contact_user)
                )
            )
            .execution_options(populate_existing=True)
        )
        companies = (await self.session.execute(companies_statement)).scalars().all()
        bookings_statement = include_deleted_for(
            select(KpEventBooking)
            .where(col(KpEventBooking.event_id) == event.id)
            .options(
                selectinload(rel(KpEventBooking.booth_zone)),
                selectinload(rel(KpEventBooking.upgrade_waitlist_entries)),
            )
            .execution_options(populate_existing=True),
            KpEventBoothZone,
        )
        bookings = (await self.session.execute(bookings_statement)).scalars().all()
        await self.end_read_transaction()
        return AudienceData(
            event=AudienceEvent(
                id=event.id,
                name=event.name,
                event_date=event.event_date,
                registration_end=event.registration_end,
                finalization_deadline=event.finalization_deadline,
                nametags_deadline=event.nametags_deadline,
            ),
            companies=[self._audience_company(company) for company in companies],
            bookings=[self._audience_booking(booking) for booking in bookings],
        )

    def _audience_company(self, company: Company) -> AudienceCompany:
        profile = company.kp_profile
        return AudienceCompany(
            id=company.id,
            name=company.name,
            contact=eligible_contact(
                profile.kp_contact_user if profile is not None else None, company.id
            ),
            general_email=profile.general_email if profile is not None else None,
        )

    def _audience_booking(self, booking: KpEventBooking) -> AudienceBooking:
        zone: KpEventBoothZone | None = getattr(booking, "booth_zone", None)
        return AudienceBooking(
            id=booking.id,
            company_id=booking.company_id,
            status=booking.status,
            booth_zone_id=booking.booth_zone_id,
            booth_zone_name=zone.name if zone is not None else "-",
            offer_deadline=booking.offer_deadline,
            waitlisted=any(
                entry.deleted_at is None for entry in booking.upgrade_waitlist_entries
            ),
        )
