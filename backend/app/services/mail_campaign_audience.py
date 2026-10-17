from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.core.utils import normalize_email
from app.mail_templates.context import MailCampaignContext, NameList
from app.models.kp_event import (
    BOOKED_STATUSES,
    INACTIVE_BOOKING_STATUSES,
    KpBookingStatus,
    KpServiceCategory,
)
from app.models.mail import (
    MailCampaignRecipientSource,
    MailCampaignSegment,
    MailCampaignSkipReason,
)
from app.models.user import User
from app.schemas.mail_campaign import MailCampaignAudience

NOT_AVAILABLE = "-"
ZONE_SEPARATOR = ", "


@dataclass(frozen=True)
class AudienceEvent:
    id: UUID
    name: str
    event_date: date
    registration_end: date
    finalization_deadline: date
    nametags_deadline: date


@dataclass(frozen=True)
class AudienceContact:
    user_id: UUID
    email: str
    name: str


@dataclass(frozen=True)
class AudienceCompany:
    id: UUID
    name: str
    contact: AudienceContact | None
    general_email: str | None
    accounts: Sequence[AudienceContact] = ()
    additional_emails: Sequence[str] = ()


@dataclass(frozen=True)
class AudienceService:
    id: UUID
    name: str
    category: KpServiceCategory


@dataclass(frozen=True)
class AudienceBooking:
    id: UUID
    company_id: UUID
    status: KpBookingStatus
    booth_zone_id: UUID
    booth_zone_name: str
    offer_deadline: date | None
    waitlisted: bool
    services: Sequence[AudienceService] = ()

    @property
    def is_active(self) -> bool:
        return self.status not in INACTIVE_BOOKING_STATUSES


@dataclass(frozen=True)
class AudienceData:
    event: AudienceEvent
    companies: Sequence[AudienceCompany]
    bookings: Sequence[AudienceBooking]

    def active_bookings(self) -> dict[UUID, list[AudienceBooking]]:
        grouped: dict[UUID, list[AudienceBooking]] = defaultdict(list)
        for booking in self.bookings:
            if booking.is_active:
                grouped[booking.company_id].append(booking)
        return grouped

    def company(self, company_id: UUID) -> AudienceCompany | None:
        return next(
            (company for company in self.companies if company.id == company_id), None
        )


@dataclass(frozen=True)
class PlannedRecipient:
    company: AudienceCompany
    email: str | None
    source: MailCampaignRecipientSource | None
    person: AudienceContact | None
    skip_reason: MailCampaignSkipReason | None
    manually_included: bool


def eligible_contact(user: User | None, company_id: UUID) -> AudienceContact | None:
    if user is None or user.is_deleted or user.company_id != company_id:
        return None
    if not user.email_confirmed or not user.email.strip():
        return None
    return AudienceContact(user_id=user.id, email=user.email, name=user.display_name)


def recipient_address(
    company: AudienceCompany,
) -> tuple[str | None, MailCampaignRecipientSource | None]:
    if company.contact is not None:
        return company.contact.email, MailCampaignRecipientSource.CONTACT
    if company.general_email and company.general_email.strip():
        return company.general_email.strip(), MailCampaignRecipientSource.GENERAL_EMAIL
    return None, None


Address = tuple[str | None, MailCampaignRecipientSource | None, AudienceContact | None]


def company_addresses(company: AudienceCompany, all_accounts: bool) -> list[Address]:
    primary: list[Address]
    if all_accounts and company.accounts:
        primary = [
            (account.email, MailCampaignRecipientSource.ACCOUNT, account)
            for account in company.accounts
        ]
    else:
        email, source = recipient_address(company)
        person = (
            company.contact if source == MailCampaignRecipientSource.CONTACT else None
        )
        primary = [(email, source, person)] if email else []
    additional: list[Address] = [
        (email, MailCampaignRecipientSource.ADDITIONAL_EMAIL, None)
        for email in company.additional_emails
    ]
    return primary + additional or [(None, None, None)]


def _booking_matches(segment: MailCampaignSegment, booking: AudienceBooking) -> bool:
    match segment:
        case MailCampaignSegment.ALL:
            return True
        case MailCampaignSegment.REGISTERED:
            return booking.status in BOOKED_STATUSES
        case MailCampaignSegment.CONFIRMED:
            return booking.status == KpBookingStatus.CONFIRMED
        case MailCampaignSegment.OFFERED:
            return booking.status == KpBookingStatus.OFFERED
        case MailCampaignSegment.WAITLISTED:
            return booking.waitlisted
        case MailCampaignSegment.NOT_REGISTERED:
            return False


def _booking_in_filters(
    audience: MailCampaignAudience, booking: AudienceBooking
) -> bool:
    zones = audience.booth_zone_ids
    if zones and booking.booth_zone_id not in zones:
        return False
    if not audience.service_ids and not audience.service_categories:
        return True
    return any(
        service.id in audience.service_ids
        or service.category in audience.service_categories
        for service in booking.services
    )


def company_matches(
    audience: MailCampaignAudience, bookings: Sequence[AudienceBooking]
) -> bool:
    narrowed = bool(
        audience.booth_zone_ids or audience.service_ids or audience.service_categories
    )
    for segment in audience.segments:
        if segment == MailCampaignSegment.NOT_REGISTERED:
            if not bookings:
                return True
            continue
        if segment == MailCampaignSegment.ALL and not narrowed:
            return True
        if any(
            _booking_matches(segment, booking)
            and _booking_in_filters(audience, booking)
            for booking in bookings
        ):
            return True
    return False


def select_companies(
    audience: MailCampaignAudience, data: AudienceData
) -> list[tuple[AudienceCompany, bool]]:
    bookings = data.active_bookings()
    included = set(audience.include_company_ids)
    excluded = set(audience.exclude_company_ids)
    selected: list[tuple[AudienceCompany, bool]] = []
    for company in data.companies:
        if company.id in excluded:
            continue
        matched = company_matches(audience, bookings.get(company.id, []))
        if matched or company.id in included:
            selected.append((company, not matched))
    return selected


def plan_recipients(
    audience: MailCampaignAudience, data: AudienceData
) -> list[PlannedRecipient]:
    selected = sorted(
        select_companies(audience, data),
        key=lambda entry: (entry[0].name.casefold(), str(entry[0].id)),
    )
    seen: set[str] = set()
    planned: list[PlannedRecipient] = []
    for company, manually_included in selected:
        for email, source, person in company_addresses(company, audience.all_accounts):
            skip_reason = None
            if email is None:
                skip_reason = MailCampaignSkipReason.NO_ADDRESS
            elif normalize_email(email) in seen:
                skip_reason = MailCampaignSkipReason.DUPLICATE_ADDRESS
            else:
                seen.add(normalize_email(email))
            planned.append(
                PlannedRecipient(
                    company=company,
                    email=email,
                    source=source,
                    person=person,
                    skip_reason=skip_reason,
                    manually_included=manually_included,
                )
            )
    return planned


def login_path(event_id: UUID, bookings: Sequence[AudienceBooking]) -> str:
    booking = next(
        (booking for booking in bookings if booking.status in BOOKED_STATUSES), None
    )
    if booking is None:
        return f"/kp/{event_id}"
    return f"/kp/{event_id}/booking"


def _names(
    services: Sequence[AudienceService], category: KpServiceCategory
) -> NameList:
    return NameList(
        service.name for service in services if service.category == category
    )


def campaign_context(
    data: AudienceData,
    company: AudienceCompany,
    person: AudienceContact | None,
    login_url: str,
) -> MailCampaignContext:
    bookings = data.active_bookings().get(company.id, [])
    zones = sorted({booking.booth_zone_name for booking in bookings})
    offer_deadlines = sorted(
        booking.offer_deadline
        for booking in bookings
        if booking.status == KpBookingStatus.OFFERED
        and booking.offer_deadline is not None
    )
    booked = sorted(
        (service for booking in bookings for service in booking.services),
        key=lambda service: service.name.casefold(),
    )
    event = data.event
    return MailCampaignContext(
        name=person.name if person is not None else company.name,
        company_name=company.name,
        event_name=event.name,
        event_date=event.event_date.isoformat(),
        registration_end=event.registration_end.isoformat(),
        finalization_deadline=event.finalization_deadline.isoformat(),
        nametags_deadline=event.nametags_deadline.isoformat(),
        booth_zone_name=ZONE_SEPARATOR.join(zones) or NOT_AVAILABLE,
        offer_deadline=offer_deadlines[0].isoformat()
        if offer_deadlines
        else NOT_AVAILABLE,
        login_url=login_url,
        services=_names(booked, KpServiceCategory.SERVICE),
        booth_elements=_names(booked, KpServiceCategory.BOOTH_ELEMENT),
    )
