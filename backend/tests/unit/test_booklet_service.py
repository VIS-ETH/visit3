from base64 import b64decode
from collections.abc import Callable
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import CompanyNotFound, NotAllowed
from app.models.company import Company, KpCompanyLanguage, KpCompanyProfile
from app.models.industry import Industry
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBoothZone,
)
from app.models.storage import StoredFile
from app.models.user import User
from app.schemas.company import UpdateCompanyProfileInput
from app.services.booklet_service import COMPANY_PAGE_TEMPLATE, BookletService
from app.services.pdf_service import PdfService, RenderedImage

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def pdf_service() -> AsyncMock:
    service = AsyncMock(spec=PdfService)
    service.render_png.return_value = RenderedImage(png=PNG_SIGNATURE, metadata=False)
    return service


@pytest.fixture
def company(make_company: Callable[..., Company]) -> Company:
    return make_company(name="Acme AG")


@pytest.fixture
def company_user(make_user: Callable[..., User], company: Company) -> User:
    return make_user(company_id=company.id)


@pytest.fixture
def prepared_repos(
    company_repo: AsyncMock, kp_repo: AsyncMock, company: Company
) -> tuple[AsyncMock, AsyncMock]:
    company_repo.get_by_id.return_value = company
    company_repo.get_kp_profile.return_value = None
    company_repo.get_industries_by_ids.return_value = []
    kp_repo.list_bookings_for_company.return_value = []
    return company_repo, kp_repo


def make_service(
    repos: tuple[AsyncMock, AsyncMock],
    storage_service: AsyncMock,
    pdf_service: AsyncMock,
    user: User,
) -> BookletService:
    company_repo, kp_repo = repos
    return BookletService(company_repo, kp_repo, storage_service, pdf_service, user)


def make_booking(
    company: Company,
    *,
    days_until_event: int,
    status: KpBookingStatus = KpBookingStatus.REGISTERED,
    booth_nr: int | None = None,
    color: str = "#112233",
) -> KpEventBooking:
    today = date.today()
    event_date = today + timedelta(days=days_until_event)
    event = KpEvent(
        id=uuid4(),
        name="Kontaktparty",
        registration_open=event_date - timedelta(days=40),
        registration_end=event_date - timedelta(days=30),
        finalization_deadline=event_date - timedelta(days=20),
        nametags_deadline=event_date - timedelta(days=10),
        event_date=event_date,
    )
    zone = KpEventBoothZone(
        id=uuid4(),
        event_id=event.id,
        name="Main hall",
        description="",
        capacity=10,
        color=color,
    )
    booking = KpEventBooking(
        id=uuid4(),
        booking_number=1000,
        event_id=event.id,
        company_id=company.id,
        booth_zone_id=zone.id,
        status=status,
        booth_nr=booth_nr,
    )
    booking.event = event
    booking.booth_zone = zone
    return booking


def rendered_entry(pdf_service: AsyncMock) -> dict[str, object]:
    return pdf_service.render_png.await_args.kwargs["data"]


async def test_the_page_shows_the_unsaved_form_values(
    prepared_repos, storage_service, pdf_service, company_user
):
    company_repo, _ = prepared_repos
    industry = Industry(id=uuid4(), name="Robotics")
    company_repo.get_industries_by_ids.return_value = [industry]
    service = make_service(prepared_repos, storage_service, pdf_service, company_user)

    await service.preview_my_company_page(
        UpdateCompanyProfileInput(
            description="Wir bauen Roboter.",
            brand_name="Acme Labs",
            website="https://acme.example",
            general_email="info@acme.example",
            general_phone="+41 44 000 00 00",
            places_of_work="Zurich",
            employee_count_worldwide=120,
            employee_count_switzerland=40,
            offers_internships=True,
            offers_theses=True,
            languages=[KpCompanyLanguage.GERMAN, KpCompanyLanguage.ENGLISH],
            industry_ids=[industry.id],
        )
    )

    assert pdf_service.render_png.await_args.kwargs["template_name"] == (
        COMPANY_PAGE_TEMPLATE
    )
    assert pdf_service.render_png.await_args.kwargs["files"] == {}
    assert rendered_entry(pdf_service) == {
        "company": "Acme AG",
        "brand_name": "Acme Labs",
        "description": "Wir bauen Roboter.",
        "website": "https://acme.example",
        "general_email": "info@acme.example",
        "general_phone": "+41 44 000 00 00",
        "places_of_work": "Zurich",
        "languages": ["German", "English"],
        "industries": ["Robotics"],
        "employee_count_worldwide": 120,
        "employee_count_switzerland": 40,
        "offers": {
            "internships": True,
            "part_time": False,
            "theses": True,
            "graduate_positions": False,
        },
        "logo_path": None,
        "zone_color": None,
        "booth_number": None,
    }


async def test_the_next_active_booking_colours_the_banner(
    prepared_repos, storage_service, pdf_service, company_user, company
):
    _, kp_repo = prepared_repos
    kp_repo.list_bookings_for_company.return_value = [
        make_booking(company, days_until_event=-10, booth_nr=1, color="#aaaaaa"),
        make_booking(
            company,
            days_until_event=5,
            status=KpBookingStatus.CANCELLED,
            booth_nr=2,
            color="#bbbbbb",
        ),
        make_booking(company, days_until_event=90, booth_nr=3, color="#cccccc"),
        make_booking(company, days_until_event=30, booth_nr=12, color="#112233"),
    ]
    service = make_service(prepared_repos, storage_service, pdf_service, company_user)

    await service.preview_my_company_page(UpdateCompanyProfileInput())

    assert rendered_entry(pdf_service)["zone_color"] == "#112233"
    assert rendered_entry(pdf_service)["booth_number"] == "12"


async def test_a_booking_without_a_booth_number_keeps_the_number_empty(
    prepared_repos, storage_service, pdf_service, company_user, company
):
    _, kp_repo = prepared_repos
    kp_repo.list_bookings_for_company.return_value = [
        make_booking(company, days_until_event=30)
    ]
    service = make_service(prepared_repos, storage_service, pdf_service, company_user)

    await service.preview_my_company_page(UpdateCompanyProfileInput())

    assert rendered_entry(pdf_service)["zone_color"] == "#112233"
    assert rendered_entry(pdf_service)["booth_number"] is None


async def test_the_stored_logo_is_placed_on_the_page(
    prepared_repos, storage_service, pdf_service, company_user, company
):
    company_repo, _ = prepared_repos
    profile = KpCompanyProfile(company_id=company.id)
    profile.logo_stored_file = StoredFile(
        storage_key="company/logo.jpg",
        original_filename="logo.jpg",
        mime_type="image/jpeg",
        size_bytes=3,
        sha256="a" * 64,
    )
    company_repo.get_kp_profile.return_value = profile
    storage_service.download_bytes.return_value = b"jpg"
    service = make_service(prepared_repos, storage_service, pdf_service, company_user)

    await service.preview_my_company_page(UpdateCompanyProfileInput())

    storage_service.download_bytes.assert_awaited_once_with("company/logo.jpg")
    assert pdf_service.render_png.await_args.kwargs["files"] == {"logo.jpg": b"jpg"}
    assert rendered_entry(pdf_service)["logo_path"] == "logo.jpg"


async def test_the_brand_falls_back_to_the_company_name(
    prepared_repos, storage_service, pdf_service, company_user
):
    service = make_service(prepared_repos, storage_service, pdf_service, company_user)

    await service.preview_my_company_page(UpdateCompanyProfileInput(brand_name="  "))

    assert rendered_entry(pdf_service)["brand_name"] == "Acme AG"


async def test_the_preview_returns_the_image_and_the_overflow_flag(
    prepared_repos, storage_service, pdf_service, company_user
):
    pdf_service.render_png.return_value = RenderedImage(
        png=PNG_SIGNATURE, metadata=True
    )
    service = make_service(prepared_repos, storage_service, pdf_service, company_user)

    result = await service.preview_my_company_page(UpdateCompanyProfileInput())

    assert b64decode(result.png_base64) == PNG_SIGNATURE
    assert result.overflow is True


async def test_staff_preview_any_company(
    prepared_repos, storage_service, pdf_service, staff_user, company
):
    service = make_service(prepared_repos, storage_service, pdf_service, staff_user)

    await service.preview_company_page(company.id, UpdateCompanyProfileInput())

    assert rendered_entry(pdf_service)["company"] == "Acme AG"


async def test_staff_preview_of_an_unknown_company_is_not_found(
    prepared_repos, storage_service, pdf_service, staff_user
):
    company_repo, _ = prepared_repos
    company_repo.get_by_id.return_value = None
    service = make_service(prepared_repos, storage_service, pdf_service, staff_user)

    with pytest.raises(CompanyNotFound):
        await service.preview_company_page(uuid4(), UpdateCompanyProfileInput())

    pdf_service.render_png.assert_not_awaited()


async def test_a_company_user_may_not_preview_another_company(
    prepared_repos, storage_service, pdf_service, company_user
):
    service = make_service(prepared_repos, storage_service, pdf_service, company_user)

    with pytest.raises(NotAllowed):
        await service.preview_company_page(uuid4(), UpdateCompanyProfileInput())

    pdf_service.render_png.assert_not_awaited()
