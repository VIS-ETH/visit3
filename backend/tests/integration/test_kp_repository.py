from datetime import date, timedelta

from sqlmodel import select

from app.models.kp_event import (
    KpEventBooking,
    KpEventBookingService,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.models.storage import StoredFile
from app.schemas.kp import (
    CreateBoothZoneInput,
    CreateIndustryInput,
    CreateKpInput,
    CreateServiceInput,
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
        CreateServiceInput(name="Electricity", order=20, price=1000),
    )
    requirement = KpEventServiceRequirement(
        service_id=service.id,
        type=KpEventServiceRequirementType.PDF,
        name="Invoice",
        description="Please upload your invoice as PDF.",
    )
    db_session.add(requirement)
    await db_session.commit()
    db_session.expunge(service)

    services = await kp_repository.list_services(event.id)
    loaded = await kp_repository.get_service_by_name(event.id, "Electricity")
    assert loaded is not None
    assert [item.name for item in loaded.requirements] == ["Invoice"]

    updated = await kp_repository.update_service(
        loaded,
        UpdateServiceInput(price=1500, is_active=False),
    )

    assert [item.id for item in services] == [service.id]
    assert updated.price == 1500
    assert updated.is_active is False


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
