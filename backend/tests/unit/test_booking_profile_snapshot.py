from collections.abc import Callable
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import CompanyProfileIncomplete, CompanyProfileUnconfirmed
from app.models.company import MANDATORY_PROFILE_FIELDS, KpCompanyProfile
from app.models.kp_event import KpEvent, KpEventBooking, KpEventBoothZone
from app.models.user import User
from app.services.kp_service import KpService


def make_event() -> KpEvent:
    today = date.today()
    return KpEvent(
        id=uuid4(),
        name="Kontaktparty",
        registration_open=today - timedelta(days=5),
        registration_end=today + timedelta(days=5),
        finalization_deadline=today + timedelta(days=6),
        nametags_deadline=today + timedelta(days=7),
        event_date=today + timedelta(days=30),
    )


def make_zone(event_id) -> KpEventBoothZone:
    zone = KpEventBoothZone(
        id=uuid4(), event_id=event_id, name="Main hall", description="", capacity=2
    )
    zone.included_services = []
    return zone


def prepare_repository(
    kp_repo: AsyncMock, event: KpEvent, zone: KpEventBoothZone, company_id
) -> KpEventBooking:
    booking = KpEventBooking(
        id=uuid4(),
        booking_number=1000,
        event_id=event.id,
        company_id=company_id,
        booth_zone_id=zone.id,
    )
    booking.booth_zone = zone
    booking.event = event
    booking.services = []
    kp_repo.get_by_id.return_value = event
    kp_repo.get_booth_zone_by_id.return_value = zone
    kp_repo.get_company_active_booking_for_event.return_value = None
    kp_repo.lock_model_by_id.side_effect = [event, zone]
    kp_repo.count_active_bookings_for_zone.return_value = 0
    kp_repo.create_booking.return_value = booking
    return booking


async def test_register_booking_refuses_an_unconfirmed_profile(
    kp_repo: AsyncMock,
    storage_service: AsyncMock,
    make_user: Callable[..., User],
):
    company_id = uuid4()
    event = make_event()
    zone = make_zone(event.id)
    prepare_repository(kp_repo, event, zone, company_id)
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))

    with pytest.raises(CompanyProfileUnconfirmed) as error:
        await service.register_booking(event.id, zone.id)

    assert error.value.code == "error.company_profile_unconfirmed"
    assert error.value.status_code == 400
    kp_repo.create_booking.assert_not_awaited()


async def test_register_booking_refuses_a_missing_profile(
    kp_repo: AsyncMock,
    storage_service: AsyncMock,
    make_user: Callable[..., User],
):
    company_id = uuid4()
    event = make_event()
    zone = make_zone(event.id)
    prepare_repository(kp_repo, event, zone, company_id)
    kp_repo.get_company_profile.return_value = None
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))

    with pytest.raises(CompanyProfileIncomplete) as error:
        await service.register_booking(event.id, zone.id, confirm_profile=True)

    assert error.value.code == "error.company_profile_incomplete"
    assert error.value.status_code == 409
    assert error.value.details == {"missingFields": list(MANDATORY_PROFILE_FIELDS)}
    kp_repo.create_booking.assert_not_awaited()


async def test_register_booking_lists_only_the_missing_fields(
    kp_repo: AsyncMock,
    storage_service: AsyncMock,
    make_user: Callable[..., User],
    make_company_profile: Callable[..., KpCompanyProfile],
):
    company_id = uuid4()
    event = make_event()
    zone = make_zone(event.id)
    prepare_repository(kp_repo, event, zone, company_id)
    kp_repo.get_company_profile.return_value = make_company_profile(
        company_id=company_id, description="", billing_city=""
    )
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))

    with pytest.raises(CompanyProfileIncomplete) as error:
        await service.register_booking(event.id, zone.id, confirm_profile=True)

    assert error.value.details == {"missingFields": ["description", "billing_city"]}


async def test_register_booking_hands_the_profile_to_the_snapshot(
    kp_repo: AsyncMock,
    storage_service: AsyncMock,
    make_user: Callable[..., User],
    make_company_profile: Callable[..., KpCompanyProfile],
):
    company_id = uuid4()
    event = make_event()
    zone = make_zone(event.id)
    prepare_repository(kp_repo, event, zone, company_id)
    profile = make_company_profile(company_id=company_id)
    kp_repo.get_company_profile.return_value = profile
    service = KpService(kp_repo, storage_service, make_user(company_id=company_id))

    await service.register_booking(event.id, zone.id, confirm_profile=True)

    assert kp_repo.create_booking.await_args.kwargs["company_profile"] is profile
