from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.deleted_filter import include_deleted
from app.models.kp_event import (
    KpBookingStatus,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZoneServiceLink,
    KpEventNametagBackground,
    KpEventRegistrationException,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
    KpServiceCategory,
)
from app.models.storage import StoredFile
from app.schemas.kp import (
    BookingServiceInput,
    CloneKpInput,
    CreateBookingInput,
    CreateBoothZoneInput,
    CreateKpInput,
    CreateServiceInput,
    NameTagInput,
    ServiceRequirementInput,
    UpdateBookingInput,
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


async def test_service_crud_loads_requirements(kp_repository):
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
            layout_description="Two tables and one standing table.",
        ),
    )
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(
            name="Electricity",
            description="Power hookup",
            category=KpServiceCategory.BOOTH_ELEMENT,
            unit_label="Stück",
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
    assert cloned_zone.layout_description == zone.layout_description
    assert cloned_service.id != service.id
    assert cloned_service.name == service.name
    assert cloned_service.category == KpServiceCategory.BOOTH_ELEMENT
    assert cloned_service.unit_label == "Stück"
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


@dataclass
class BookingContext:
    event_id: UUID
    company_id: UUID
    zone_id: UUID
    included_service_id: UUID
    extra_service_id: UUID
    included_link: KpEventBoothZoneServiceLink


async def create_booking_context(
    kp_repository,
    company_repository,
    db_session,
    *,
    included_quantity: int = 2,
) -> BookingContext:
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Acme AG")
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main"),
    )
    included_service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(name="Chairs", max_quantity_per_booking=10),
    )
    extra_service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(name="Power", max_quantity_per_booking=10),
    )
    included_link = KpEventBoothZoneServiceLink(
        booth_zone_id=zone.id,
        service_id=included_service.id,
        included_quantity=included_quantity,
    )
    db_session.add(included_link)
    await db_session.commit()
    return BookingContext(
        event_id=event.id,
        company_id=company.id,
        zone_id=zone.id,
        included_service_id=included_service.id,
        extra_service_id=extra_service.id,
        included_link=included_link,
    )


async def test_create_booking_stores_requested_quantity_as_total(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository,
        company_repository,
        db_session,
        included_quantity=2,
    )

    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
        services=[
            BookingServiceInput(service_id=context.included_service_id, quantity=3),
            BookingServiceInput(service_id=context.extra_service_id, quantity=1),
        ],
        included_services=[context.included_link],
    )

    by_service_id = {item.service_id: item for item in booking.services}
    included = by_service_id[context.included_service_id]
    extra = by_service_id[context.extra_service_id]
    assert (included.quantity, included.included_quantity) == (3, 2)
    assert included.charged_quantity == 1
    assert (extra.quantity, extra.included_quantity) == (1, 0)
    assert extra.charged_quantity == 1


async def test_create_booking_raises_quantity_to_included_amount(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository,
        company_repository,
        db_session,
        included_quantity=3,
    )

    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
        services=[
            BookingServiceInput(service_id=context.included_service_id, quantity=1),
        ],
        included_services=[context.included_link],
    )

    included = booking.services[0]
    assert (included.quantity, included.included_quantity) == (3, 3)
    assert included.charged_quantity == 0


async def test_create_booking_adds_unrequested_included_service(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository,
        company_repository,
        db_session,
        included_quantity=2,
    )

    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
        included_services=[context.included_link],
    )

    included = booking.services[0]
    assert included.service_id == context.included_service_id
    assert (included.quantity, included.included_quantity) == (2, 2)
    assert included.charged_quantity == 0


async def test_add_booking_services_increments_total_quantity(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository,
        company_repository,
        db_session,
        included_quantity=2,
    )
    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
        included_services=[context.included_link],
    )

    updated = await kp_repository.add_booking_services(
        booking,
        [BookingServiceInput(service_id=context.included_service_id, quantity=1)],
    )

    included = updated.services[0]
    assert (included.quantity, included.included_quantity) == (3, 2)
    assert included.charged_quantity == 1


async def test_count_active_charged_service_quantity_ignores_included_and_cancelled(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository,
        company_repository,
        db_session,
        included_quantity=2,
    )
    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
        services=[
            BookingServiceInput(service_id=context.included_service_id, quantity=5),
        ],
        included_services=[context.included_link],
    )
    cancelled_company = await company_repository.create_company("Cancelled AG")
    cancelled_booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=cancelled_company.id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(status=KpBookingStatus.CANCELLED),
        services=[
            BookingServiceInput(service_id=context.included_service_id, quantity=4),
        ],
        included_services=[context.included_link],
    )

    charged = await kp_repository.count_active_charged_service_quantity(
        context.included_service_id
    )

    assert booking.services[0].charged_quantity == 3
    assert cancelled_booking.services[0].charged_quantity == 2
    assert charged == 3


async def test_replace_waitlist_entries_reorders_existing_targets(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    first_target = await kp_repository.create_booth_zone(
        context.event_id,
        CreateBoothZoneInput(name="Gold", color="#111111"),
    )
    second_target = await kp_repository.create_booth_zone(
        context.event_id,
        CreateBoothZoneInput(name="Silver", color="#222222"),
    )

    created = await kp_repository.replace_booking_upgrade_waitlist_entries(
        booking,
        [first_target.id, second_target.id],
    )
    created_order = [
        (entry.target_booth_zone_id, entry.priority_rank) for entry in created
    ]

    reordered = await kp_repository.replace_booking_upgrade_waitlist_entries(
        booking,
        [second_target.id, first_target.id],
    )

    assert created_order == [(first_target.id, 1), (second_target.id, 2)]
    assert [
        (entry.target_booth_zone_id, entry.priority_rank) for entry in reordered
    ] == [
        (second_target.id, 1),
        (first_target.id, 2),
    ]


async def test_get_booking_service_loads_booking_event(
    kp_repository,
    company_repository,
    db_session,
):
    booking_service, _ = await create_requirement_answer_context(
        kp_repository,
        company_repository,
        db_session,
    )
    db_session.expunge_all()

    loaded = await kp_repository.get_booking_service_by_id(booking_service.id)

    assert loaded is not None
    assert loaded.booking.event.id == loaded.booking.event_id


async def test_delete_booth_zone_soft_deletes_zone_and_removes_links(
    kp_repository,
    company_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Acme AG")
    kept_zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main", color="#000001"),
    )
    removed_zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Side", color="#000002"),
    )
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(name="Power"),
    )
    booking = KpEventBooking(
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=kept_zone.id,
        booking_number=1000,
    )
    db_session.add(booking)
    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=removed_zone.id,
            service_id=service.id,
        )
    )
    await db_session.commit()
    db_session.add(
        KpEventBookingUpgradeWaitlist(
            booking_id=booking.id,
            target_booth_zone_id=removed_zone.id,
        )
    )
    await db_session.commit()

    await kp_repository.delete_booth_zone(removed_zone)
    db_session.expunge_all()

    remaining_links = (
        (
            await db_session.execute(
                include_deleted(
                    select(KpEventBoothZoneServiceLink).where(
                        KpEventBoothZoneServiceLink.booth_zone_id == removed_zone.id
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    waitlist_entries = await kp_repository.list_booking_upgrade_waitlist_entries(
        booking.id
    )
    zones = await kp_repository.list_booth_zones(event.id)

    assert remaining_links == []
    assert waitlist_entries == []
    assert [zone.id for zone in zones] == [kept_zone.id]
    assert await kp_repository.get_booth_zone_by_id(removed_zone.id) is None


async def test_delete_booth_zone_frees_waitlist_pairs(
    kp_repository,
    company_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Acme AG")
    home_zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main", color="#000001"),
    )
    removed_zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Side", color="#000002"),
    )
    booking = KpEventBooking(
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=home_zone.id,
        booking_number=1000,
    )
    db_session.add(booking)
    await db_session.commit()
    await kp_repository.replace_booking_upgrade_waitlist_entries(
        booking, [removed_zone.id]
    )

    await kp_repository.delete_booth_zone(removed_zone)
    db_session.expunge_all()

    stored_entries = (
        (
            await db_session.execute(
                include_deleted(
                    select(KpEventBookingUpgradeWaitlist).where(
                        KpEventBookingUpgradeWaitlist.target_booth_zone_id
                        == removed_zone.id
                    )
                )
            )
        )
        .scalars()
        .all()
    )

    assert stored_entries == []

    db_session.add(
        KpEventBookingUpgradeWaitlist(
            booking_id=booking.id,
            target_booth_zone_id=removed_zone.id,
        )
    )
    await db_session.commit()


async def test_get_booth_zone_by_id_reloads_included_services(
    kp_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(name="Power"),
    )
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main", color="#000001"),
    )

    stale = await kp_repository.get_booth_zone_by_id(zone.id)
    assert stale is not None
    assert stale.included_services == []

    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=zone.id,
            service_id=service.id,
            included_quantity=3,
        )
    )
    await db_session.commit()

    reloaded = await kp_repository.get_booth_zone_by_id(zone.id)

    assert reloaded is not None
    assert [
        (link.service_id, link.included_quantity) for link in reloaded.included_services
    ] == [(service.id, 3)]


async def test_get_booth_zone_by_name_and_color_reload_included_services(
    kp_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(name="Power"),
    )
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main", color="#000001"),
    )

    stale = await kp_repository.get_booth_zone_by_name(event.id, "Main")
    assert stale is not None
    assert stale.included_services == []

    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=zone.id,
            service_id=service.id,
            included_quantity=2,
        )
    )
    await db_session.commit()

    by_name = await kp_repository.get_booth_zone_by_name(event.id, "Main")
    by_color = await kp_repository.get_booth_zone_by_color(event.id, "#000001")

    assert by_name is not None
    assert by_color is not None
    assert [
        (link.service_id, link.included_quantity) for link in by_name.included_services
    ] == [(service.id, 2)]
    assert [
        (link.service_id, link.included_quantity) for link in by_color.included_services
    ] == [(service.id, 2)]


async def test_delete_service_soft_deletes_requirements_and_frees_image(
    kp_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main"),
    )
    removed_service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(
            name="Power",
            requirements=[
                ServiceRequirementInput(
                    type=KpEventServiceRequirementType.PDF,
                    name="Invoice",
                    description="Please upload your invoice as PDF.",
                )
            ],
        ),
    )
    kept_service = await kp_repository.create_service(
        event.id,
        CreateServiceInput(name="Chairs"),
    )
    image = await kp_repository.upsert_stored_file(
        storage_key="service-image.png",
        original_filename="image.png",
        mime_type="image/png",
        size_bytes=3,
        sha256="a" * 64,
        etag="image",
    )
    await kp_repository.set_service_image_stored_file_id(removed_service, image.id)
    image.updated_at = image.updated_at - timedelta(hours=48)
    db_session.add(image)
    db_session.add(
        KpEventBoothZoneServiceLink(
            booth_zone_id=zone.id,
            service_id=removed_service.id,
        )
    )
    await db_session.commit()

    await kp_repository.delete_service(removed_service)
    db_session.expunge_all()

    services = await kp_repository.list_services(event.id)
    remaining_links = (
        (
            await db_session.execute(
                include_deleted(
                    select(KpEventBoothZoneServiceLink).where(
                        KpEventBoothZoneServiceLink.service_id == removed_service.id
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    remaining_requirements = (
        (
            await db_session.execute(
                select(KpEventServiceRequirement).where(
                    KpEventServiceRequirement.service_id == removed_service.id
                )
            )
        )
        .scalars()
        .all()
    )
    orphaned = await kp_repository.list_orphaned_stored_files(max_age_hours=24)

    assert [service.id for service in services] == [kept_service.id]
    assert await kp_repository.get_service_by_id(removed_service.id) is None
    assert remaining_links == []
    assert remaining_requirements == []
    assert [file.storage_key for file in orphaned] == ["service-image.png"]


async def test_cancelled_booking_frees_the_zone_for_the_same_company(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    cancelled = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(status=KpBookingStatus.CANCELLED),
    )

    reregistered = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )

    assert reregistered.id != cancelled.id

    db_session.add(
        KpEventBooking(
            event_id=context.event_id,
            company_id=context.company_id,
            booth_zone_id=context.zone_id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_rejected_booking_frees_the_zone_and_its_capacity(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    rejected = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(status=KpBookingStatus.REJECTED),
    )

    assert (
        await kp_repository.count_active_bookings_for_zone(
            context.event_id, context.zone_id
        )
        == 0
    )

    reregistered = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )

    assert reregistered.id != rejected.id
    assert (
        await kp_repository.count_active_bookings_for_zone(
            context.event_id, context.zone_id
        )
        == 1
    )


async def test_booth_numbers_are_unique_among_active_bookings_only(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    cancelled = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(status=KpBookingStatus.CANCELLED),
    )
    reusing_company = await company_repository.create_company("Reuse AG")
    reusing = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=reusing_company.id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )

    await kp_repository.update_booking(cancelled, UpdateBookingInput(booth_nr=7))
    await kp_repository.update_booking(reusing, UpdateBookingInput(booth_nr=7))

    assert reusing.booth_nr == 7

    colliding_company = await company_repository.create_company("Collide AG")
    db_session.add(
        KpEventBooking(
            event_id=context.event_id,
            company_id=colliding_company.id,
            booth_zone_id=context.zone_id,
            booth_nr=7,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_booth_numbers_can_be_cleared_on_several_bookings(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    first = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    second_company = await company_repository.create_company("Second AG")
    second = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=second_company.id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    await kp_repository.update_booking(first, UpdateBookingInput(booth_nr=1))
    await kp_repository.update_booking(second, UpdateBookingInput(booth_nr=2))

    await kp_repository.update_booking(first, UpdateBookingInput(booth_nr=None))
    await kp_repository.update_booking(second, UpdateBookingInput(booth_nr=None))

    assert (first.booth_nr, second.booth_nr) == (None, None)


async def test_soft_deleted_nametag_background_frees_the_event(
    kp_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    files = [
        await kp_repository.upsert_stored_file(
            storage_key=f"replaced-{index}.png",
            original_filename=f"replaced-{index}.png",
            mime_type="image/png",
            size_bytes=3,
            sha256=str(index) * 64,
            etag=f"replaced-{index}",
        )
        for index in range(2)
    ]
    background = await kp_repository.upsert_nametag_background(event.id, files[0].id)

    kp_repository.delete(background)
    await db_session.commit()
    replacement = await kp_repository.upsert_nametag_background(event.id, files[1].id)

    assert replacement.id != background.id
    assert replacement.stored_file_id == files[1].id


async def test_nametag_background_stays_unique_per_event(
    kp_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    files = [
        await kp_repository.upsert_stored_file(
            storage_key=f"background-{index}.png",
            original_filename=f"background-{index}.png",
            mime_type="image/png",
            size_bytes=3,
            sha256=str(index) * 64,
            etag=f"background-{index}",
        )
        for index in range(3)
    ]

    created = await kp_repository.upsert_nametag_background(event.id, files[0].id)
    replaced = await kp_repository.upsert_nametag_background(event.id, files[1].id)

    assert replaced.id == created.id
    assert replaced.stored_file_id == files[1].id

    db_session.add(
        KpEventNametagBackground(event_id=event.id, stored_file_id=files[2].id)
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_zone_layout_file_is_not_cleaned_up_as_an_orphan(
    kp_repository,
    db_session,
):
    event = await kp_repository.create_kp(make_kp_input())
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main"),
    )
    layout_file = await kp_repository.upsert_stored_file(
        storage_key="zone-layout.png",
        original_filename="layout.png",
        mime_type="image/png",
        size_bytes=3,
        sha256="c" * 64,
        etag="layout",
    )
    await kp_repository.set_booth_zone_layout_stored_file_id(zone, layout_file.id)
    layout_file.updated_at = layout_file.updated_at - timedelta(hours=48)
    db_session.add(layout_file)
    await db_session.commit()

    orphaned = await kp_repository.list_orphaned_stored_files(max_age_hours=24)

    assert orphaned == []


async def test_replace_name_tags_swaps_the_whole_list(
    kp_repository,
    company_repository,
):
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Acme AG")
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main"),
    )
    booking = await kp_repository.create_booking(
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=zone.id,
        create_booking_input=CreateBookingInput(),
    )
    await kp_repository.replace_name_tags(
        booking,
        [NameTagInput(first_name="Ada", last_name="Lovelace", position="Engineer")],
    )

    replaced = await kp_repository.replace_name_tags(
        booking,
        [NameTagInput(first_name="Grace", last_name="Hopper", position="Admiral")],
    )

    assert [tag.first_name for tag in replaced] == ["Grace"]
    stored = await kp_repository.list_name_tags_for_booking(booking.id)
    assert [tag.first_name for tag in stored] == ["Grace"]


async def test_replace_name_tags_with_an_empty_list_clears_them(
    kp_repository,
    company_repository,
):
    event = await kp_repository.create_kp(make_kp_input())
    company = await company_repository.create_company("Beta GmbH")
    zone = await kp_repository.create_booth_zone(
        event.id,
        CreateBoothZoneInput(name="Main"),
    )
    booking = await kp_repository.create_booking(
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=zone.id,
        create_booking_input=CreateBookingInput(),
    )
    await kp_repository.replace_name_tags(
        booking,
        [NameTagInput(first_name="Ada", last_name="Lovelace", position="Engineer")],
    )

    assert await kp_repository.replace_name_tags(booking, []) == []


async def create_upgrade_zone(
    kp_repository,
    db_session,
    context: BookingContext,
    *,
    name: str = "Gold",
    color: str = "#123456",
    capacity: int = 1,
    included_service_id: UUID | None = None,
    included_quantity: int = 4,
):
    zone = await kp_repository.create_booth_zone(
        context.event_id,
        CreateBoothZoneInput(name=name, color=color, capacity=capacity),
    )
    if included_service_id is not None:
        db_session.add(
            KpEventBoothZoneServiceLink(
                booth_zone_id=zone.id,
                service_id=included_service_id,
                included_quantity=included_quantity,
            )
        )
        await db_session.commit()
    return await kp_repository.get_booth_zone_by_id(zone.id)


async def test_move_booking_to_zone_recomputes_inclusions(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session, included_quantity=2
    )
    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
        services=[
            BookingServiceInput(service_id=context.included_service_id, quantity=3),
            BookingServiceInput(service_id=context.extra_service_id, quantity=1),
        ],
        included_services=[context.included_link],
    )
    target = await create_upgrade_zone(
        kp_repository,
        db_session,
        context,
        included_service_id=context.extra_service_id,
        included_quantity=4,
    )

    moved = await kp_repository.move_booking_to_zone(
        booking, target, clear_whole_waitlist=False
    )

    by_service_id = {item.service_id: item for item in moved.services}
    included = by_service_id[context.included_service_id]
    extra = by_service_id[context.extra_service_id]
    assert moved.booth_zone_id == target.id
    assert (included.quantity, included.included_quantity) == (3, 0)
    assert (extra.quantity, extra.included_quantity) == (4, 4)


async def test_move_booking_to_zone_adds_newly_included_services(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    target = await create_upgrade_zone(
        kp_repository,
        db_session,
        context,
        included_service_id=context.extra_service_id,
        included_quantity=2,
    )

    moved = await kp_repository.move_booking_to_zone(
        booking, target, clear_whole_waitlist=False
    )

    assert [
        (item.service_id, item.quantity, item.included_quantity)
        for item in moved.services
    ] == [(context.extra_service_id, 2, 2)]


async def test_move_booking_to_zone_clears_the_booth_number(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    booking = await kp_repository.update_booking(
        booking, UpdateBookingInput(booth_nr=7)
    )
    target = await create_upgrade_zone(kp_repository, db_session, context)

    moved = await kp_repository.move_booking_to_zone(
        booking, target, clear_whole_waitlist=False
    )

    assert moved.booth_nr is None
    assert moved.status == KpBookingStatus.REGISTERED


async def test_move_booking_to_zone_drops_only_the_target_waitlist_entry(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    target = await create_upgrade_zone(kp_repository, db_session, context)
    other = await create_upgrade_zone(
        kp_repository, db_session, context, name="Silver", color="#654321"
    )
    await kp_repository.replace_booking_upgrade_waitlist_entries(
        booking, [target.id, other.id]
    )

    moved = await kp_repository.move_booking_to_zone(
        booking, target, clear_whole_waitlist=False
    )
    remaining = await kp_repository.list_booking_upgrade_waitlist_entries(moved.id)

    assert [entry.target_booth_zone_id for entry in remaining] == [other.id]


async def test_move_booking_to_zone_clears_the_whole_waitlist(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    booking = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    target = await create_upgrade_zone(kp_repository, db_session, context)
    other = await create_upgrade_zone(
        kp_repository, db_session, context, name="Silver", color="#654321"
    )
    await kp_repository.replace_booking_upgrade_waitlist_entries(
        booking, [target.id, other.id]
    )

    moved = await kp_repository.move_booking_to_zone(
        booking, target, clear_whole_waitlist=True
    )

    assert await kp_repository.list_booking_upgrade_waitlist_entries(moved.id) == []


async def test_waitlist_entries_for_zone_are_ordered_by_rank(
    kp_repository,
    company_repository,
    db_session,
):
    context = await create_booking_context(
        kp_repository, company_repository, db_session
    )
    target = await create_upgrade_zone(kp_repository, db_session, context)
    other_zone = await create_upgrade_zone(
        kp_repository, db_session, context, name="Silver", color="#654321"
    )
    first = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=context.company_id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    second_company = await company_repository.create_company("Beta GmbH")
    second = await kp_repository.create_booking(
        event_id=context.event_id,
        company_id=second_company.id,
        booth_zone_id=context.zone_id,
        create_booking_input=CreateBookingInput(),
    )
    await kp_repository.replace_booking_upgrade_waitlist_entries(
        second, [other_zone.id, target.id]
    )
    await kp_repository.replace_booking_upgrade_waitlist_entries(first, [target.id])

    entries = await kp_repository.list_waitlist_entries_for_zone(target.id)

    assert [(entry.booking_id, entry.priority_rank) for entry in entries] == [
        (first.id, 1),
        (second.id, 2),
    ]

    await kp_repository.delete_waitlist_entry(entries[0])

    assert [
        entry.booking_id
        for entry in await kp_repository.list_waitlist_entries_for_zone(target.id)
    ] == [second.id]


def make_future_kp_input(name: str = "Upcoming Kontaktparty") -> CreateKpInput:
    today = date.today()
    return CreateKpInput(
        name=name,
        registration_open=today - timedelta(days=5),
        registration_end=today + timedelta(days=5),
        finalization_deadline=today + timedelta(days=6),
        nametags_deadline=today + timedelta(days=7),
        event_date=today + timedelta(days=30),
    )


async def test_bookings_awaiting_reminder_skip_past_events_and_sent_reminders(
    kp_repository,
    company_repository,
    db_session,
):
    upcoming = await kp_repository.create_kp(make_future_kp_input())
    past = await kp_repository.create_kp(make_kp_input("Past Kontaktparty"))
    upcoming_zone = await kp_repository.create_booth_zone(
        upcoming.id, CreateBoothZoneInput(name="Main")
    )
    past_zone = await kp_repository.create_booth_zone(
        past.id, CreateBoothZoneInput(name="Main")
    )
    waiting_company = await company_repository.create_company("Acme AG")
    reminded_company = await company_repository.create_company("Beta GmbH")
    past_company = await company_repository.create_company("Gamma SA")
    waiting = await kp_repository.create_booking(
        event_id=upcoming.id,
        company_id=waiting_company.id,
        booth_zone_id=upcoming_zone.id,
        create_booking_input=CreateBookingInput(),
    )
    reminded = await kp_repository.create_booking(
        event_id=upcoming.id,
        company_id=reminded_company.id,
        booth_zone_id=upcoming_zone.id,
        create_booking_input=CreateBookingInput(),
    )
    await kp_repository.create_booking(
        event_id=past.id,
        company_id=past_company.id,
        booth_zone_id=past_zone.id,
        create_booking_input=CreateBookingInput(),
    )
    await kp_repository.update_booking(
        reminded, UpdateBookingInput(reminder_sent_at=datetime.now(timezone.utc))
    )

    due = await kp_repository.list_registered_bookings_awaiting_reminder(date.today())

    assert [booking.id for booking in due] == [waiting.id]
