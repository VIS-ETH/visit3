from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.deleted_filter import include_deleted
from app.models.kp_event import KpEvent, KpEventBoothZone
from app.models.storage import StoredFile
from app.models.venue import KpVenueBooth, KpVenueZoneShape
from app.repositories.kp_repository import KpRepository
from app.repositories.venue_repository import VenueRepository
from app.schemas.kp import CreateBoothZoneInput, CreateKpInput
from app.schemas.venue import (
    CreateVenueLayoutInput,
    VenueBoothInput,
    VenuePolygonShape,
    VenueZoneShapeInput,
)

TRIANGLE = VenuePolygonShape(type="polygon", points=[(0, 0), (10, 0), (10, 10)])
SQUARE = VenuePolygonShape(type="polygon", points=[(0, 0), (20, 0), (20, 20)])


def make_kp_input(name: str = "Kontaktparty") -> CreateKpInput:
    today = date.today()
    return CreateKpInput(
        name=name,
        registration_open=today - timedelta(days=5),
        registration_end=today + timedelta(days=5),
        finalization_deadline=today + timedelta(days=6),
        nametags_deadline=today + timedelta(days=7),
        event_date=today + timedelta(days=30),
    )


@pytest.fixture
async def event(kp_repository: KpRepository) -> KpEvent:
    return await kp_repository.create_kp(make_kp_input())


@pytest.fixture
async def booth_zone(kp_repository: KpRepository, event: KpEvent) -> KpEventBoothZone:
    return await kp_repository.create_booth_zone(
        event.id, CreateBoothZoneInput(name="Main hall", capacity=3)
    )


async def test_layout_background_is_not_reported_as_orphaned(
    kp_repository: KpRepository,
    venue_repository: VenueRepository,
    db_session: AsyncSession,
    event: KpEvent,
):
    background = StoredFile(
        storage_key="venue-background.png",
        original_filename="plan.png",
        mime_type="image/png",
        size_bytes=3,
        sha256="c" * 64,
    )
    db_session.add(background)
    await db_session.commit()
    await db_session.refresh(background)
    background.updated_at = background.updated_at - timedelta(hours=48)
    db_session.add(background)
    await db_session.commit()
    layout = await venue_repository.create_layout(
        event.id, CreateVenueLayoutInput(name="Einstein")
    )

    await venue_repository.set_layout_background_stored_file_id(layout, background.id)
    orphaned = await kp_repository.list_orphaned_stored_files(max_age_hours=24)

    assert orphaned == []


async def test_replaced_shapes_leave_no_rows_behind(
    venue_repository: VenueRepository,
    db_session: AsyncSession,
    event: KpEvent,
    booth_zone: KpEventBoothZone,
):
    layout = await venue_repository.create_layout(
        event.id, CreateVenueLayoutInput(name="Einstein")
    )
    await venue_repository.replace_zone_shapes(
        layout,
        [VenueZoneShapeInput(booth_zone_id=booth_zone.id, shape=TRIANGLE)],
    )

    kept = await venue_repository.replace_zone_shapes(
        layout,
        [VenueZoneShapeInput(booth_zone_id=booth_zone.id, shape=SQUARE)],
    )
    every_row = (
        (
            await db_session.execute(
                include_deleted(
                    select(KpVenueZoneShape).where(
                        col(KpVenueZoneShape.layout_id) == layout.id
                    )
                )
            )
        )
        .scalars()
        .all()
    )

    assert [shape.shape for shape in kept] == [SQUARE.model_dump(mode="json")]
    assert len(every_row) == 1


async def test_replaced_booths_leave_no_rows_behind(
    venue_repository: VenueRepository,
    db_session: AsyncSession,
    event: KpEvent,
    booth_zone: KpEventBoothZone,
):
    layout = await venue_repository.create_layout(
        event.id, CreateVenueLayoutInput(name="Einstein")
    )
    booth = VenueBoothInput(booth_zone_id=booth_zone.id, booth_nr=1, x=1, y=1)
    await venue_repository.replace_booths(layout, [booth])

    kept = await venue_repository.replace_booths(layout, [booth])
    every_row = (
        (
            await db_session.execute(
                include_deleted(
                    select(KpVenueBooth).where(col(KpVenueBooth.layout_id) == layout.id)
                )
            )
        )
        .scalars()
        .all()
    )

    assert [entry.booth_nr for entry in kept] == [1]
    assert len(every_row) == 1
