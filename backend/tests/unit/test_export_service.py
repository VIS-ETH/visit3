from dataclasses import dataclass
from datetime import datetime, timezone
from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    KpBookingNotFound,
    KpEventNotFound,
    KpExportBackgroundNotFound,
    KpExportEmpty,
    KpNameTagNotFound,
)
from app.services.export_service import ExportService, RenderedExport


@dataclass
class ExportServiceHarness:
    service: ExportService
    kp_repo: AsyncMock
    storage_service: AsyncMock
    pdf_service: AsyncMock
    csv_service: AsyncMock


@pytest.fixture
def export_service(kp_repo, storage_service, staff_user):
    pdf_service = AsyncMock()
    csv_service = MagicMock()
    csv_service.render_csv.return_value = (b"csv-content", "export.csv")
    csv_service.render_zip.return_value = (b"zip-content", "export.zip")
    service = ExportService(
        kp_repo,
        storage_service,
        pdf_service,
        csv_service,
        staff_user,
    )
    return ExportServiceHarness(
        service=service,
        kp_repo=kp_repo,
        storage_service=storage_service,
        pdf_service=pdf_service,
        csv_service=cast(AsyncMock, csv_service),
    )


def test_safe_filename_part_normalizes_value(export_service):
    service = export_service.service

    assert service._safe_filename_part("Hello World!") == "hello-world"
    assert service._safe_filename_part("  ") == "export"
    assert service._safe_filename_part("A&B_C") == "a-b_c"


def test_export_filename_delegates_to_sanitize(export_service):
    assert export_service.service._export_filename("report.csv") == "report.csv"


def test_bool_and_money_helpers(export_service):
    service = export_service.service

    assert service._bool(True) == "yes"
    assert service._bool(False) == "no"
    assert service._money(12345) == "123.45"
    assert service._money(0) == "0.00"


def test_languages_and_industries_helpers(export_service):
    service = export_service.service

    assert service._languages(["de", "en"]) == "de, en"
    assert service._languages([]) == ""

    booking = MagicMock()
    booking.company_details = None
    assert service._industries(booking) == ""


@pytest.mark.asyncio
async def test_upload_nametag_background_requires_event(export_service):
    event_id = uuid4()
    export_service.kp_repo.get_by_id.return_value = None

    with pytest.raises(KpEventNotFound):
        await export_service.service.upload_nametag_background(
            event_id, "bg.png", b"content", "image/png"
        )


@pytest.mark.asyncio
async def test_get_nametag_background_delegates_to_repository(export_service):
    event_id = uuid4()
    export_service.kp_repo.get_nametag_background.return_value = None

    result = await export_service.service.get_nametag_background(event_id)

    assert result is None
    export_service.kp_repo.get_nametag_background.assert_awaited_once_with(event_id)


@pytest.mark.asyncio
async def test_list_nametag_export_targets_returns_sorted_results(
    export_service,
):
    event_id = uuid4()

    def make_booking(company_name: str, zone_name: str, booth_nr: int):
        booking = MagicMock()
        booking.id = uuid4()
        booking.company_id = uuid4()
        booking.company.name = company_name
        booking.booth_zone.name = zone_name
        booking.booth_nr = booth_nr
        return booking

    booking_a = make_booking("Beta GmbH", "B", 2)
    booking_b = make_booking("Alpha AG", "A", 1)
    tag_a = MagicMock()
    tag_a.id = uuid4()
    tag_a.first_name = "Zoe"
    tag_a.last_name = "Zebra"
    tag_a.position = "Engineer"
    tag_b = MagicMock()
    tag_b.id = uuid4()
    tag_b.first_name = "Anna"
    tag_b.last_name = "Alpha"
    tag_b.position = "Manager"
    booking_a.name_tags = [tag_a]
    booking_b.name_tags = [tag_b]

    export_service.kp_repo.get_by_id.return_value = object()
    export_service.kp_repo.list_bookings_for_event.return_value = [
        booking_a,
        booking_b,
    ]

    result = await export_service.service.list_nametag_export_targets(event_id)

    assert [c.company_name for c in result.companies] == ["Alpha AG", "Beta GmbH"]
    assert [p.first_name for p in result.people] == ["Anna", "Zoe"]


@pytest.mark.asyncio
async def test_render_event_nametags_requires_event(export_service):
    export_service.kp_repo.get_by_id.return_value = None

    with pytest.raises(KpEventNotFound):
        await export_service.service.render_event_nametags(uuid4())


@pytest.mark.asyncio
async def test_render_booking_nametags_raises_when_booking_missing(
    export_service,
):
    export_service.kp_repo.get_booking_by_id.return_value = None

    with pytest.raises(KpBookingNotFound):
        await export_service.service.render_booking_nametags(uuid4())


@pytest.mark.asyncio
async def test_render_single_nametag_raises_when_missing(export_service):
    export_service.kp_repo.get_name_tag_by_id.return_value = None

    with pytest.raises(KpNameTagNotFound):
        await export_service.service.render_single_nametag(uuid4())


@pytest.mark.asyncio
async def test_get_background_bytes_raises_when_missing(export_service):
    event_id = uuid4()
    export_service.kp_repo.get_nametag_background.return_value = None

    with pytest.raises(KpExportBackgroundNotFound):
        await export_service.service._get_background_bytes(event_id)


@pytest.mark.asyncio
async def test_render_nametags_pdf_raises_when_empty(export_service):
    with pytest.raises(KpExportEmpty):
        await export_service.service._render_nametags_pdf(
            b"png", "image/png", [], "nametags.pdf", 2
        )


@pytest.mark.asyncio
async def test_render_nametags_pdf_returns_rendered_export(export_service):
    export_service.pdf_service.render_with_workspace.return_value = (
        b"pdf",
        "nametags.pdf",
    )

    name_tag = MagicMock()
    name_tag.first_name = "Ada"
    name_tag.last_name = "Lovelace"
    name_tag.position = "Engineer"
    name_tag.booking.company.name = "Acme"

    result = await export_service.service._render_nametags_pdf(
        b"png", "image/png", [name_tag], "nametags.pdf", 2
    )

    assert isinstance(result, RenderedExport)
    assert result.content == b"pdf"


def _assert_render_csv_filename(export_service, expected_filename):
    export_service.csv_service.render_csv.assert_called_once()
    assert export_service.csv_service.render_csv.call_args.args[1] == expected_filename


@pytest.mark.asyncio
async def test_export_bookings_csv_returns_rendered_csv(export_service):
    event_id = uuid4()
    event = MagicMock()
    event.name = "VIS 2026"
    booking = MagicMock()
    booking.id = uuid4()
    booking.company.name = "Acme"
    booking.status.value = "confirmed"
    booking.booth_zone.name = "A"
    booking.booth_nr = 1
    booking.booth_zone.booth_size = 9
    booking.booth_zone.base_price = 50000
    booking.services = []
    booking.name_tags = []
    export_service.kp_repo.get_by_id.return_value = event
    export_service.kp_repo.list_bookings_for_event.return_value = [booking]

    await export_service.service.export_bookings_csv(event_id)

    _assert_render_csv_filename(export_service, "VIS 2026-bookings-all.csv")


@pytest.mark.asyncio
async def test_export_waitlist_companies_csv_maps_entries(export_service):
    event_id = uuid4()
    event = MagicMock()
    event.name = "VIS 2026"
    booking = MagicMock()
    booking.id = uuid4()
    booking.company.name = "Acme"
    booking.status.value = "confirmed"
    booking.booth_zone.name = "A"
    booking.booth_nr = 1
    entry = MagicMock()
    entry.target_booth_zone.name = "B"
    entry.priority_rank = 1
    booking.upgrade_waitlist_entries = [entry]
    export_service.kp_repo.get_by_id.return_value = event
    export_service.kp_repo.list_bookings_for_event.return_value = [booking]

    await export_service.service.export_waitlist_companies_csv(event_id)

    _assert_render_csv_filename(
        export_service, "VIS 2026-waitlist-companies.csv"
    )


@pytest.mark.asyncio
async def test_export_booked_services_csv_maps_services(export_service):
    event_id = uuid4()
    event = MagicMock()
    event.name = "VIS 2026"
    booking = MagicMock()
    booking.id = uuid4()
    booking.company.name = "Acme"
    booking.booth_zone.name = "A"
    booking.booth_nr = 1
    booking_service = MagicMock()
    booking_service.service.name = "Catering"
    booking_service.service.price = 10000
    booking_service.quantity = 2
    booking_service.included_quantity = 0
    booking_service.charged_quantity = 2
    booking.services = [booking_service]
    export_service.kp_repo.get_by_id.return_value = event
    export_service.kp_repo.list_bookings_for_event.return_value = [booking]

    await export_service.service.export_booked_services_csv(event_id)

    _assert_render_csv_filename(export_service, "VIS 2026-booked-services.csv")


@pytest.mark.asyncio
async def test_export_nametags_data_csv_maps_name_tags(export_service):
    event_id = uuid4()
    event = MagicMock()
    event.name = "VIS 2026"
    name_tag = MagicMock()
    name_tag.id = uuid4()
    name_tag.booking_id = uuid4()
    name_tag.booking.company.name = "Acme"
    name_tag.first_name = "Ada"
    name_tag.last_name = "Lovelace"
    name_tag.position = "Engineer"
    export_service.kp_repo.get_by_id.return_value = event
    export_service.kp_repo.list_name_tags_for_event.return_value = [name_tag]

    await export_service.service.export_nametags_data_csv(event_id)

    _assert_render_csv_filename(export_service, "VIS 2026-nametags-data.csv")


@pytest.mark.asyncio
async def test_export_company_details_csv_maps_details(export_service):
    event_id = uuid4()
    event = MagicMock()
    event.name = "VIS 2026"
    booking = MagicMock()
    booking.id = uuid4()
    booking.company.name = "Acme"
    booking.booth_zone.name = "A"
    booking.booth_nr = 1
    details = MagicMock()
    details.brand_name = "Acme Brand"
    details.address = "Zurich"
    details.contact_person = "Ada"
    details.places_of_work = "Zurich"
    details.employees_count = "100"
    details.employees_count_switzerland = "50"
    details.offer_internship = True
    details.offer_part_time = False
    details.offer_thesis = True
    details.languages = ["de", "en"]
    details.profile = "We do things"
    details.industry_links = []
    booking.company_details = details
    export_service.kp_repo.get_by_id.return_value = event
    export_service.kp_repo.list_bookings_for_event.return_value = [booking]

    await export_service.service.export_company_details_csv(event_id)

    _assert_render_csv_filename(export_service, "VIS 2026-company-details.csv")


@pytest.mark.asyncio
async def test_export_booth_zone_capacity_csv_maps_zones(export_service):
    event_id = uuid4()
    event = MagicMock()
    event.name = "VIS 2026"
    booking = MagicMock()
    booking.booth_zone_id = uuid4()
    booking.upgrade_waitlist_entries = []
    zone = MagicMock()
    zone.id = booking.booth_zone_id
    zone.name = "A"
    zone.capacity = 10
    zone.booth_size = 9
    zone.base_price = 50000
    export_service.kp_repo.get_by_id.return_value = event
    export_service.kp_repo.list_bookings_for_event.return_value = [booking]
    export_service.kp_repo.list_booth_zones.return_value = [zone]

    await export_service.service.export_booth_zone_capacity_csv(event_id)

    _assert_render_csv_filename(
        export_service, "VIS 2026-booth-zone-capacity.csv"
    )


@pytest.mark.asyncio
async def test_export_contacts_csv_maps_profiles(export_service):
    event_id = uuid4()
    event = MagicMock()
    event.name = "VIS 2026"
    booking = MagicMock()
    booking.id = uuid4()
    booking.company.name = "Acme"
    booking.company.users = []
    profile = MagicMock()
    profile.contact_email = "contact@example.com"
    profile.invoice_address = "Invoice"
    profile.shipping_address = "Shipping"
    profile.kp_contact_user = None
    booking.company.kp_profile = profile
    export_service.kp_repo.get_by_id.return_value = event
    export_service.kp_repo.list_bookings_for_event.return_value = [booking]

    await export_service.service.export_contacts_csv(event_id)

    _assert_render_csv_filename(export_service, "VIS 2026-contacts.csv")


@pytest.mark.asyncio
async def test_export_registration_exceptions_csv_maps_exceptions(
    export_service,
):
    event_id = uuid4()
    event = MagicMock()
    event.name = "VIS 2026"
    exception = MagicMock()
    exception.company.name = "Acme"
    exception.company_id = uuid4()
    exception.allowed_until = datetime.now(timezone.utc)
    export_service.kp_repo.get_by_id.return_value = event
    export_service.kp_repo.list_registration_exceptions.return_value = [exception]

    await export_service.service.export_registration_exceptions_csv(event_id)

    _assert_render_csv_filename(
        export_service, "VIS 2026-registration-exceptions.csv"
    )
