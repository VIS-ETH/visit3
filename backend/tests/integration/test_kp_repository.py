from datetime import date, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.models.kp_event import (
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBoothZoneServiceLink,
    KpEventNametagBackground,
    KpEventRegistrationException,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.models.storage import StoredFile
from app.schemas.kp import (
    CloneKpInput,
    CreateBoothZoneInput,
    CreateIndustryInput,
    CreateKpInput,
    CreateServiceInput,
    ServiceRequirementInput,
    UpdateBoothZoneInput,
    UpdateServiceInput,
)


def make_kp_input(name: str = "Kontaktparty") -> CreateKpInput:
    today = date.today()
    return CreateKpInput(
        name=name,
        registration_open=today - timedelta(days=10),
        registration_end=today - timedelta(days=5),
        finalization_deadline=today - timedelta(days=4),
        nametags_deadline=today - timedelta(days=3),
        event_date=today + timedelta(days=10),
    )


async def create_requirement_answer_context(
    kp_repository,
    company_repository,
    db_session,
    *,
    requirement_type: KpEventServiceRequirementType = KpEventServiceRequirementType.PDF,
) -> tuple[KpEventBookingService, KpEventServiceRequirement]:
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Acme AG")
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main"),
    )
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(name="Electricity"),
    )
    booking = KpEventBooking(
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=zone.id,
        booking_number=1000,
    )
    requirement = KpEventServiceRequirement(
        service_id=service.id,
        type=requirement_type,
        name="Invoice",
        description="Please upload your invoice as PDF.",
    )
    db_session.add(booking)
    db_session.add(requirement)
    await db_session.commit()
    await db_session.refresh(booking)
    await db_session.refresh(requirement)
    booking_service = KpEventBookingService(
        booking_id=booking.id,
        service_id=service.id,
    )
    db_session.add(booking_service)
    await db_session.commit()
    await db_session.refresh(booking_service)
    return booking_service, requirement


async def test_create_and_list_kps_orders_latest_first(kp_repository):
    older = await kp_repository.create_kp(make_kp_input("KP Old"))
    newer_input = make_kp_input("KP New")
    newer_input.event_date = older.event_date + timedelta(days=1)
    newer = await kp_repository.create_kp(newer_input)

    result = await kp_repository.list_kps()
    latest = await kp_repository.get_latest_kp()

    assert [event.id for event in result] == [newer.id, older.id]
    assert latest == newer


async def test_booth_zone_crud_and_ordering(kp_repository):
    event = await kp_repository.create_kp(make_kp_input())
    later = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Zeta", color="#000001", order=20, capacity=3),
    )
    earlier = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Alpha", color="#000002", order=10, capacity=1),
    )

    zones = await kp_repository.list_booth_zones(event.id)
    loaded = await kp_repository.get_booth_zone_by_name(event.id, "Alpha")
    updated = await kp_repository.update_booth_zone(
        earlier,
        UpdateBoothZoneInput(capacity=5, color="#123ABC"),
    )

    assert [zone.id for zone in zones] == [earlier.id, later.id]
    assert loaded == earlier
    assert updated.capacity == 5
    assert updated.color == "#123ABC"


async def test_service_crud_loads_requirements(kp_repository, db_session):
    event = await kp_repository.create_kp(make_kp_input())
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(
            name="Electricity",
            order=20,
            price=1000,
            requirements=[
                ServiceRequirementInput(
                    type=KpEventServiceRequirementType.PDF,
                    name="Invoice",
                    description="Please upload your invoice as PDF.",
                )
            ],
        ),
    )
    db_session.expunge(service)

    services = await kp_repository.list_services(event.id)
    loaded = await kp_repository.get_service_by_name(event.id, "Electricity")
    assert loaded is not None
    assert [item.name for item in loaded.requirements] == ["Invoice"]
    requirement = loaded.requirements[0]

    updated = await kp_repository.update_service(
        loaded,
        UpdateServiceInput(
            price=1500,
            is_active=False,
            requirements=[
                ServiceRequirementInput(
                    id=requirement.id,
                    type=KpEventServiceRequirementType.IMAGE,
                    name="Logo",
                    description="Please upload your company logo.",
                    order=10,
                )
            ],
        ),
    )

    assert [item.id for item in services] == [service.id]
    assert updated.price == 1500
    assert updated.is_active is False
    assert [(item.name, item.type, item.order) for item in updated.requirements] == [
        ("Logo", KpEventServiceRequirementType.IMAGE, 10)
    ]


async def test_clone_kp_copies_setup_without_bookings_exceptions_or_background(
    kp_repository,
    company_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Acme AG")
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(
            name="Main",
            description="Main zone",
            color="#112233",
            order=10,
            capacity=5,
            booth_size=12.5,
            base_price=25000,
        ),
    )
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(
            name="Electricity",
            description="Power hookup",
            confirmation_description="Bring your adapter.",
            order=20,
            price=1000,
            max_quantity_per_booking=2,
            max_total_quantity=10,
            is_active=False,
        ),
    )
    requirement = KpEventServiceRequirement(
        service_id=service.id,
        type=KpEventServiceRequirementType.PDF,
        name="Invoice",
        description="Please upload your invoice as PDF.",
        order=30,
    )
    included_service = KpEventBoothZoneServiceLink(
        booth_zone_id=zone.id,
        service_id=service.id,
        included_quantity=2,
    )
    booking = KpEventBooking(
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=zone.id,
        booking_number=1000,
    )
    registration_exception = KpEventRegistrationException(
        event_id=event.id,
        company_id=company.id,
        allowed_until=date.today() + timedelta(days=1),
    )
    background_file = StoredFile(
        storage_key="background.png",
        original_filename="background.png",
        mime_type="image/png",
        size_bytes=3,
        sha256="a" * 64,
    )
    db_session.add(requirement)
    db_session.add(included_service)
    db_session.add(booking)
    db_session.add(registration_exception)
    db_session.add(background_file)
    await db_session.commit()
    await db_session.refresh(background_file)
    background = KpEventNametagBackground(
        event_id=event.id,
        stored_file_id=background_file.id,
    )
    db_session.add(background)
    await db_session.commit()
    db_session.expunge_all()

    clone_input = make_kp_input("Kontaktparty Clone")
    clone_input.event_date = event.event_date + timedelta(days=30)
    cloned = await kp_repository.clone_kp(
        event.id,
        CloneKpInput(**clone_input.model_dump()),
    )

    assert cloned is not None
    assert cloned.id != event.id
    assert cloned.name == "Kontaktparty Clone"
    assert cloned.event_date == clone_input.event_date

    cloned_zones = await kp_repository.list_booth_zones(cloned.id)
    cloned_services = await kp_repository.list_services(cloned.id)

    assert len(cloned_zones) == 1
    assert len(cloned_services) == 1
    cloned_zone = cloned_zones[0]
    cloned_service = cloned_services[0]
    assert cloned_zone.id != zone.id
    assert cloned_zone.name == zone.name
    assert cloned_zone.color == zone.color
    assert cloned_zone.base_price == zone.base_price
    assert cloned_service.id != service.id
    assert cloned_service.name == service.name
    assert cloned_service.is_active is False
    assert [item.name for item in cloned_service.requirements] == ["Invoice"]
    assert cloned_service.requirements[0].id != requirement.id
    assert cloned_service.requirements[0].service_id == cloned_service.id
    assert len(cloned_zone.included_services) == 1
    assert cloned_zone.included_services[0].service_id == cloned_service.id
    assert cloned_zone.included_services[0].included_quantity == 2

    cloned_bookings = (
        (
            await db_session.execute(
                select(KpEventBooking).where(KpEventBooking.event_id == cloned.id)
            )
        )
        .scalars()
        .all()
    )
    cloned_exceptions = (
        (
            await db_session.execute(
                select(KpEventRegistrationException).where(
                    KpEventRegistrationException.event_id == cloned.id
                )
            )
        )
        .scalars()
        .all()
    )
    cloned_background = (
        await db_session.execute(
            select(KpEventNametagBackground).where(
                KpEventNametagBackground.event_id == cloned.id
            )
        )
    ).scalar_one_or_none()

    assert cloned_bookings == []
    assert cloned_exceptions == []
    assert cloned_background is None


async def test_clone_kp_carries_advertisement_service_id_through_service_remap(
    kp_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(
            name="Booklet ad",
            description="Single-page advertisement",
            requirements=[
                ServiceRequirementInput(
                    type=KpEventServiceRequirementType.PDF_SINGLE_PAGE,
                    name="Ad PDF",
                    description="Single-page PDF for the booklet placement.",
                )
            ],
        ),
    )
    await kp_repository.set_advertisement_service_id(event, service.id)
    db_session.expunge_all()

    clone_input = make_kp_input("Kontaktparty Ad Clone")
    cloned = await kp_repository.clone_kp(
        event.id,
        CloneKpInput(**clone_input.model_dump()),
    )

    assert cloned is not None
    assert cloned.advertisement_service_id is not None
    assert cloned.advertisement_service_id != service.id

    cloned_services = await kp_repository.list_services(cloned.id)
    assert len(cloned_services) == 1
    assert cloned.advertisement_service_id == cloned_services[0].id


async def test_industry_crud_orders_by_name(kp_repository):
    zeta = await kp_repository.create_industry(CreateIndustryInput(name="Zeta"))
    alpha = await kp_repository.create_industry(CreateIndustryInput(name="Alpha"))

    industries = await kp_repository.list_industries()
    loaded = await kp_repository.get_industry_by_name("Alpha")

    assert [industry.id for industry in industries] == [alpha.id, zeta.id]
    assert loaded == alpha


async def test_registration_exception_upsert_and_delete(
    kp_repository,
    company_repository,
):
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Acme AG")
    first_until = date.today() + timedelta(days=1)
    second_until = date.today() + timedelta(days=2)

    created = await kp_repository.upsert_registration_exception(
        event.id,
        company.id,
        first_until,
    )
    updated = await kp_repository.upsert_registration_exception(
        event.id,
        company.id,
        second_until,
    )
    listed = await kp_repository.list_registration_exceptions(event.id)

    assert updated.id == created.id
    assert updated.allowed_until == second_until
    assert [item.id for item in listed] == [created.id]

    await kp_repository.delete_registration_exception(updated)

    assert await kp_repository.get_registration_exception(event.id, company.id) is None


async def test_requirement_file_link_upsert_replaces_stored_file(
    kp_repository,
    company_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Acme AG")
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main"),
    )
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(name="Electricity"),
    )
    booking = KpEventBooking(
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=zone.id,
        booking_number=1000,
    )
    requirement = KpEventServiceRequirement(
        service_id=service.id,
        type=KpEventServiceRequirementType.PDF,
        name="Invoice",
        description="Please upload your invoice as PDF.",
    )
    db_session.add(booking)
    db_session.add(requirement)
    await db_session.commit()
    await db_session.refresh(booking)
    await db_session.refresh(requirement)
    booking_service = KpEventBookingService(
        booking_id=booking.id,
        service_id=service.id,
    )
    db_session.add(booking_service)
    await db_session.commit()
    await db_session.refresh(booking_service)
    first_file = await kp_repository.upsert_stored_file(
        storage_key="old.pdf",
        original_filename="old.pdf",
        mime_type="application/pdf",
        size_bytes=3,
        sha256="a" * 64,
        etag="old",
    )
    second_file = await kp_repository.upsert_stored_file(
        storage_key="new.pdf",
        original_filename="new.pdf",
        mime_type="application/pdf",
        size_bytes=3,
        sha256="b" * 64,
        etag="new",
    )

    created = await kp_repository.upsert_requirement_file_link(
        booking_service.id,
        requirement.id,
        first_file.id,
    )
    updated = await kp_repository.upsert_requirement_file_link(
        booking_service.id,
        requirement.id,
        second_file.id,
    )

    assert updated.id == created.id
    assert updated.stored_file.storage_key == "new.pdf"


async def test_requirement_text_answer_upsert_replaces_file_answer(
    kp_repository,
    company_repository,
    db_session,
):
    booking_service, requirement = await create_requirement_answer_context(
        kp_repository,
        company_repository,
        db_session,
        requirement_type=KpEventServiceRequirementType.TEXT,
    )
    stored_file = await kp_repository.upsert_stored_file(
        storage_key="old.txt",
        original_filename="old.txt",
        mime_type="text/plain",
        size_bytes=3,
        sha256="a" * 64,
        etag="old",
    )
    created = await kp_repository.upsert_requirement_file_link(
        booking_service.id,
        requirement.id,
        stored_file.id,
    )

    updated = await kp_repository.upsert_requirement_text_answer(
        booking_service.id,
        requirement.id,
        "Use this slogan.",
    )

    assert updated.id == created.id
    assert updated.text_value == "Use this slogan."
    assert updated.stored_file_id is None
    assert updated.stored_file is None


async def test_requirement_file_link_upsert_replaces_text_answer(
    kp_repository,
    company_repository,
    db_session,
):
    booking_service, requirement = await create_requirement_answer_context(
        kp_repository,
        company_repository,
        db_session,
    )
    created = await kp_repository.upsert_requirement_text_answer(
        booking_service.id,
        requirement.id,
        "Initial notes.",
    )
    stored_file = await kp_repository.upsert_stored_file(
        storage_key="new.pdf",
        original_filename="new.pdf",
        mime_type="application/pdf",
        size_bytes=3,
        sha256="b" * 64,
        etag="new",
    )

    updated = await kp_repository.upsert_requirement_file_link(
        booking_service.id,
        requirement.id,
        stored_file.id,
    )

    assert updated.id == created.id
    assert updated.text_value is None
    assert updated.stored_file_id == stored_file.id
    assert updated.stored_file.storage_key == "new.pdf"


@pytest.mark.parametrize(
    ("with_file", "text_value"),
    [
        (False, None),
        (True, "Both values are not allowed."),
    ],
)
async def test_requirement_answer_requires_exactly_one_text_or_file(
    kp_repository,
    company_repository,
    db_session,
    with_file,
    text_value,
):
    booking_service, requirement = await create_requirement_answer_context(
        kp_repository,
        company_repository,
        db_session,
    )
    stored_file = None
    if with_file:
        stored_file = await kp_repository.upsert_stored_file(
            storage_key="invalid.pdf",
            original_filename="invalid.pdf",
            mime_type="application/pdf",
            size_bytes=3,
            sha256="c" * 64,
            etag="invalid",
        )
    answer = KpEventBookingServiceFileLink(
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        stored_file_id=stored_file.id if stored_file else None,
        text_value=text_value,
    )
    db_session.add(answer)

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_nametag_background_upsert_and_orphaned_files(
    kp_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    old_file = StoredFile(
        storage_key="old-background.png",
        original_filename="old.png",
        mime_type="image/png",
        size_bytes=3,
        sha256="a" * 64,
    )
    linked_file = StoredFile(
        storage_key="linked-background.png",
        original_filename="linked.png",
        mime_type="image/png",
        size_bytes=3,
        sha256="b" * 64,
    )
    db_session.add(old_file)
    db_session.add(linked_file)
    await db_session.commit()
    await db_session.refresh(old_file)
    await db_session.refresh(linked_file)
    old_file.updated_at = old_file.updated_at - timedelta(hours=48)
    linked_file.updated_at = linked_file.updated_at - timedelta(hours=48)
    db_session.add(old_file)
    db_session.add(linked_file)
    await db_session.commit()

    background = await kp_repository.upsert_nametag_background(
        event.id,
        linked_file.id,
    )
    orphaned = await kp_repository.list_orphaned_stored_files(max_age_hours=24)

    assert background.stored_file.storage_key == "linked-background.png"
    assert [file.storage_key for file in orphaned] == ["old-background.png"]

    await kp_repository.delete_stored_file(old_file)

    remaining = (
        await db_session.execute(select(StoredFile).where(StoredFile.id == old_file.id))
    ).scalar_one_or_none()
    assert remaining is None
