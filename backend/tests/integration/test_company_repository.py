from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.deleted_filter import include_deleted
from app.models.base import BaseEntity
from app.models.company import Company, CompanyInvite, KpCompanyProfile
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventRegistrationException,
    KpEventService,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
    NameTag,
)
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import UpdateCompanyProfileInput


@dataclass
class CompanyBookingFixture:
    company: Company
    booking: KpEventBooking
    booking_service: KpEventBookingService
    file_link: KpEventBookingServiceFileLink
    name_tag: NameTag
    waitlist_entry: KpEventBookingUpgradeWaitlist
    company_details: KpBookingCompanyDetails
    registration_exception: KpEventRegistrationException


def make_event(event_date: date, name: str = "Kontaktparty") -> KpEvent:
    return KpEvent(
        name=name,
        registration_open=event_date - timedelta(days=40),
        registration_end=event_date - timedelta(days=30),
        finalization_deadline=event_date - timedelta(days=20),
        nametags_deadline=event_date - timedelta(days=10),
        event_date=event_date,
    )


async def create_company_with_booking(
    company_repository: CompanyRepository,
    db_session: AsyncSession,
    *,
    event_date: date,
    company_name: str = "Acme AG",
) -> CompanyBookingFixture:
    company = await company_repository.create_company(company_name)
    event = make_event(event_date)
    db_session.add(event)
    await db_session.commit()

    booth_zone = KpEventBoothZone(event_id=event.id, name="Main", description="Main")
    target_zone = KpEventBoothZone(
        event_id=event.id, name="Premium", description="Top", color="#FF00FF"
    )
    service = KpEventService(event_id=event.id, name="Electricity", description="Power")
    db_session.add_all([booth_zone, target_zone, service])
    await db_session.commit()

    requirement = KpEventServiceRequirement(
        service_id=service.id,
        type=KpEventServiceRequirementType.TEXT,
        name="Slogan",
        description="Please tell us your company slogan.",
    )
    booking = KpEventBooking(
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=booth_zone.id,
    )
    db_session.add_all([requirement, booking])
    await db_session.commit()

    booking_service = KpEventBookingService(
        booking_id=booking.id, service_id=service.id
    )
    name_tag = NameTag(
        booking_id=booking.id, first_name="Ada", last_name="Lovelace", position="CEO"
    )
    waitlist_entry = KpEventBookingUpgradeWaitlist(
        booking_id=booking.id, target_booth_zone_id=target_zone.id
    )
    company_details = KpBookingCompanyDetails(
        booking_id=booking.id, languages=[], confirmed_at=datetime.now(timezone.utc)
    )
    registration_exception = KpEventRegistrationException(
        event_id=event.id,
        company_id=company.id,
        allowed_until=event_date - timedelta(days=1),
    )
    db_session.add_all(
        [
            booking_service,
            name_tag,
            waitlist_entry,
            company_details,
            registration_exception,
        ]
    )
    await db_session.commit()

    file_link = KpEventBookingServiceFileLink(
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        text_value="Best company ever",
    )
    db_session.add(file_link)
    await db_session.commit()

    return CompanyBookingFixture(
        company=company,
        booking=booking,
        booking_service=booking_service,
        file_link=file_link,
        name_tag=name_tag,
        waitlist_entry=waitlist_entry,
        company_details=company_details,
        registration_exception=registration_exception,
    )


async def deleted_at_of(
    db_session: AsyncSession, model: type[BaseEntity], entity_id: UUID
) -> datetime | None:
    statement = include_deleted(select(model).where(col(model.id) == entity_id))
    result = await db_session.execute(statement)
    return result.scalar_one().deleted_at


async def test_assign_user_sets_company_and_loads_relationship(
    company_repository,
    user_repository,
):
    company = await company_repository.create_company("Acme AG")
    user = await user_repository.create_user(
        User(email="member@example.com", password="hash")
    )

    result = await company_repository.assign_user(user, company.id)

    assert result.company_id == company.id
    assert result.company.name == "Acme AG"


async def test_remove_user_from_company_clears_kp_contact(
    company_repository,
    user_repository,
    db_session,
):
    company = await company_repository.create_company("Acme AG")
    user = await user_repository.create_user(
        User(email="contact@example.com", password="hash", company_id=company.id)
    )
    profile = KpCompanyProfile(
        company_id=company.id,
        kp_contact_user_id=user.id,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    result = await company_repository.remove_user_from_company(user, company)

    assert result.company_id is None
    refreshed_profile = await company_repository.get_kp_profile(company.id)
    assert refreshed_profile is not None
    assert refreshed_profile.kp_contact_user_id is None


async def test_invite_lifecycle(company_repository):
    company = await company_repository.create_company("Acme AG")
    invite = await company_repository.create_invite(
        token="invite-token",
        company_id=company.id,
        invited_email="guest@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    loaded = await company_repository.get_invite_by_token("invite-token")
    assert loaded == invite
    assert loaded is not None
    assert loaded.is_used is False

    await company_repository.mark_invite_used(loaded)
    used = await company_repository.get_invite_by_token("invite-token")
    assert used is not None
    assert used.is_used is True


async def test_upsert_kp_profile_creates_then_updates_profile(
    company_repository,
    user_repository,
):
    company = await company_repository.create_company("Acme AG")
    contact = await user_repository.create_user(
        User(email="contact@example.com", password="hash", company_id=company.id)
    )

    created = await company_repository.upsert_kp_profile(
        company.id,
        UpdateCompanyProfileInput(
            billing_street="Invoice",
            general_email="info@example.com",
            kp_contact_user_id=contact.id,
        ),
    )
    updated = await company_repository.upsert_kp_profile(
        company.id,
        UpdateCompanyProfileInput(
            billing_street="Updated Invoice",
            general_email="updated@example.com",
        ),
    )

    assert updated.id == created.id
    assert updated.billing_street == "Updated Invoice"
    assert updated.general_email == "updated@example.com"
    assert updated.kp_contact_user_id is None
    assert updated.profile_completed_at is None


async def test_delete_company_keep_users_soft_deletes_company_and_unassigns_users(
    company_repository,
    user_repository,
    db_session,
):
    company = await company_repository.create_company("Acme AG")
    user = await user_repository.create_user(
        User(email="member@example.com", password="hash", company_id=company.id)
    )

    await company_repository.delete_company_keep_users(company)

    assert await company_repository.get_by_id(company.id) is None
    refreshed_user = await user_repository.get_by_id(user.id)
    assert refreshed_user is not None
    assert refreshed_user.company_id is None
    result = await db_session.execute(include_deleted(select(Company)))
    deleted_company = result.scalar_one()
    assert deleted_company.deleted_at is not None


async def test_delete_company_with_users_soft_deletes_owned_rows(
    company_repository,
    user_repository,
    db_session,
):
    company = await company_repository.create_company("Acme AG")
    await user_repository.create_user(
        User(email="member@example.com", password="hash", company_id=company.id)
    )
    await company_repository.create_invite(
        token="invite-token",
        company_id=company.id,
        invited_email="guest@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    profile = KpCompanyProfile(
        company_id=company.id,
    )
    db_session.add(profile)
    await db_session.commit()

    await company_repository.delete_company_with_users(company)

    assert await company_repository.get_by_id(company.id) is None
    assert await user_repository.get_by_email("member@example.com") is None
    result = await db_session.execute(include_deleted(select(CompanyInvite)))
    deleted_invite = result.scalar_one()
    assert deleted_invite.deleted_at is not None


@pytest.mark.parametrize(
    "delete_method",
    ["delete_company_with_users", "delete_company_keep_users"],
)
async def test_delete_company_cascades_to_booking_owned_rows(
    delete_method,
    company_repository,
    db_session,
):
    fixture = await create_company_with_booking(
        company_repository,
        db_session,
        event_date=date.today() - timedelta(days=1),
    )

    await getattr(company_repository, delete_method)(fixture.company)

    assert await deleted_at_of(db_session, Company, fixture.company.id) is not None
    assert (
        await deleted_at_of(db_session, KpEventBooking, fixture.booking.id) is not None
    )
    assert await deleted_at_of(db_session, NameTag, fixture.name_tag.id) is not None
    assert (
        await deleted_at_of(
            db_session, KpEventBookingUpgradeWaitlist, fixture.waitlist_entry.id
        )
        is not None
    )
    assert (
        await deleted_at_of(
            db_session, KpBookingCompanyDetails, fixture.company_details.id
        )
        is not None
    )
    assert (
        await deleted_at_of(
            db_session,
            KpEventRegistrationException,
            fixture.registration_exception.id,
        )
        is not None
    )


async def test_delete_company_keeps_booking_services_linked_to_deleted_booking(
    company_repository,
    db_session,
):
    fixture = await create_company_with_booking(
        company_repository,
        db_session,
        event_date=date.today() - timedelta(days=1),
    )

    await company_repository.delete_company_with_users(fixture.company)

    booking_service = (
        await db_session.execute(
            include_deleted(
                select(KpEventBookingService).where(
                    col(KpEventBookingService.id) == fixture.booking_service.id
                )
            )
        )
    ).scalar_one()
    file_link = (
        await db_session.execute(
            include_deleted(
                select(KpEventBookingServiceFileLink).where(
                    col(KpEventBookingServiceFileLink.id) == fixture.file_link.id
                )
            )
        )
    ).scalar_one()

    assert booking_service.deleted_at is None
    assert booking_service.booking_id == fixture.booking.id
    assert file_link.deleted_at is None
    assert file_link.booking_service_id == fixture.booking_service.id


async def test_has_bookings_for_upcoming_events_ignores_past_events(
    company_repository,
    db_session,
):
    past = await create_company_with_booking(
        company_repository,
        db_session,
        event_date=date.today() - timedelta(days=1),
        company_name="Past AG",
    )

    assert (
        await company_repository.has_bookings_for_upcoming_events(past.company.id)
        is False
    )


async def test_has_bookings_for_upcoming_events_detects_today_and_future(
    company_repository,
    db_session,
):
    upcoming = await create_company_with_booking(
        company_repository,
        db_session,
        event_date=date.today(),
        company_name="Today AG",
    )

    assert (
        await company_repository.has_bookings_for_upcoming_events(upcoming.company.id)
        is True
    )


async def test_has_bookings_for_upcoming_events_ignores_cancelled_bookings(
    company_repository,
    db_session,
):
    upcoming = await create_company_with_booking(
        company_repository,
        db_session,
        event_date=date.today() + timedelta(days=5),
        company_name="Cancelled AG",
    )
    upcoming.booking.status = KpBookingStatus.CANCELLED
    db_session.add(upcoming.booking)
    await db_session.commit()

    assert (
        await company_repository.has_bookings_for_upcoming_events(upcoming.company.id)
        is False
    )


async def test_company_overviews_count_members_and_active_bookings(
    company_repository, db_session
):
    fixture = await create_company_with_booking(
        company_repository, db_session, event_date=date.today() + timedelta(days=30)
    )
    db_session.add(User(email="member@example.com", company_id=fixture.company.id))
    empty = await company_repository.create_company("Zeta AG")
    await db_session.commit()

    overviews = await company_repository.get_company_overviews()

    assert overviews == [
        (fixture.company.id, fixture.company.name, 1, 1, 0),
        (empty.id, empty.name, 0, 0, 0),
    ]


async def test_company_overviews_ignore_cancelled_bookings(
    company_repository, db_session
):
    fixture = await create_company_with_booking(
        company_repository, db_session, event_date=date.today() + timedelta(days=30)
    )
    fixture.booking.status = KpBookingStatus.CANCELLED
    db_session.add(fixture.booking)
    await db_session.commit()

    overviews = await company_repository.get_company_overviews()

    assert overviews == [(fixture.company.id, fixture.company.name, 0, 0, 0)]


async def test_company_overviews_are_searchable_and_paged(
    company_repository, db_session
):
    await company_repository.create_company("Alpha AG")
    beta = await company_repository.create_company("Beta Robotics")
    await company_repository.create_company("Gamma Robotics")

    matches = await company_repository.get_company_overviews("robotics", 0, 1)
    total = await company_repository.count_companies("robotics")

    assert [name for _, name, _, _, _ in matches] == [beta.name]
    assert total == 2


async def test_last_member_of_a_booked_company_is_detected(
    company_repository, db_session
):
    fixture = await create_company_with_booking(
        company_repository, db_session, event_date=date.today() + timedelta(days=30)
    )
    member = User(email="member@example.com", company_id=fixture.company.id)
    db_session.add(member)
    await db_session.commit()

    assert (
        await company_repository.is_last_member_of_booked_company(fixture.company.id)
        is True
    )

    db_session.add(User(email="second@example.com", company_id=fixture.company.id))
    await db_session.commit()

    assert (
        await company_repository.is_last_member_of_booked_company(fixture.company.id)
        is False
    )


async def test_last_member_without_upcoming_bookings_is_removable(
    company_repository, db_session
):
    fixture = await create_company_with_booking(
        company_repository, db_session, event_date=date.today() - timedelta(days=1)
    )
    db_session.add(User(email="member@example.com", company_id=fixture.company.id))
    await db_session.commit()

    assert (
        await company_repository.is_last_member_of_booked_company(fixture.company.id)
        is False
    )
