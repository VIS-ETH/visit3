from base64 import b64encode
from collections.abc import Sequence
from datetime import date
from uuid import UUID

from app.core.auth_context import require_company_profile_user, require_staff_user
from app.core.exceptions import CompanyNotFound
from app.core.rich_text import rich_text_blocks
from app.models.company import Company, KpCompanyLanguage
from app.models.industry import Industry
from app.models.kp_event import INACTIVE_BOOKING_STATUSES, KpEventBooking
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.schemas.company import (
    BookletPageResult,
    CompanyProfileFields,
    UpdateCompanyProfileInput,
)
from app.services.pdf_service import PdfService
from app.services.storage_service import StorageService

COMPANY_PAGE_TEMPLATE = "company_page.typ"
OVERFLOW_LABEL = "overflow"
LOGO_SUFFIXES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
LANGUAGE_NAMES = {
    KpCompanyLanguage.ENGLISH: "English",
    KpCompanyLanguage.GERMAN: "German",
    KpCompanyLanguage.FRENCH: "French",
    KpCompanyLanguage.ITALIAN: "Italian",
}


def upcoming_booking(
    bookings: Sequence[KpEventBooking], today: date
) -> KpEventBooking | None:
    upcoming = [
        booking
        for booking in bookings
        if booking.status not in INACTIVE_BOOKING_STATUSES
        and booking.event.event_date >= today
    ]
    return min(upcoming, key=lambda booking: booking.event.event_date, default=None)


def company_page_entry(
    company: Company,
    profile: CompanyProfileFields,
    industries: Sequence[Industry],
    booking: KpEventBooking | None,
    logo_path: str | None,
) -> dict[str, object]:
    return {
        "company": company.name,
        "brand_name": profile.brand_name.strip() or company.name,
        "description_blocks": rich_text_blocks(profile.description),
        "website": profile.website,
        "general_email": profile.general_email,
        "general_phone": profile.general_phone,
        "places_of_work": profile.places_of_work,
        "languages": [LANGUAGE_NAMES[language] for language in profile.languages],
        "industries": sorted(industry.name for industry in industries),
        "employee_count_worldwide": profile.employee_count_worldwide,
        "employee_count_switzerland": profile.employee_count_switzerland,
        "offers": {
            "internships": profile.offers_internships,
            "part_time": profile.offers_part_time,
            "theses": profile.offers_theses,
            "graduate_positions": profile.offers_graduate_positions,
        },
        "logo_path": logo_path,
        "zone_color": booking.booth_zone.color if booking is not None else None,
        "booth_number": str(booking.booth_nr)
        if booking is not None and booking.booth_nr is not None
        else None,
    }


class BookletService:
    def __init__(
        self,
        company_repository: CompanyRepository,
        kp_repository: KpRepository,
        storage_service: StorageService,
        pdf_service: PdfService,
        current_user: User,
    ) -> None:
        self.company_repository = company_repository
        self.kp_repository = kp_repository
        self.storage_service = storage_service
        self.pdf_service = pdf_service
        self.current_user = current_user

    async def preview_my_company_page(
        self, profile: UpdateCompanyProfileInput
    ) -> BookletPageResult:
        company_user = require_company_profile_user(self.current_user)
        return await self._preview(company_user.company_id, profile)

    async def preview_company_page(
        self, company_id: UUID, profile: UpdateCompanyProfileInput
    ) -> BookletPageResult:
        require_staff_user(self.current_user)
        return await self._preview(company_id, profile)

    async def _preview(
        self, company_id: UUID, profile: UpdateCompanyProfileInput
    ) -> BookletPageResult:
        company = await self.company_repository.get_by_id(company_id)
        if company is None:
            raise CompanyNotFound(f"booklet_page:{company_id}")
        industries: Sequence[Industry] = (
            await self.company_repository.get_industries_by_ids(
                list(dict.fromkeys(profile.industry_ids))
            )
            if profile.industry_ids
            else ()
        )
        bookings = await self.kp_repository.list_bookings_for_company(company_id)
        files = await self._logo_files(company_id)
        rendered = await self.pdf_service.render_png(
            template_name=COMPANY_PAGE_TEMPLATE,
            data=company_page_entry(
                company,
                profile,
                industries,
                upcoming_booking(bookings, date.today()),
                next(iter(files), None),
            ),
            files=files,
            metadata_label=OVERFLOW_LABEL,
        )
        return BookletPageResult(
            png_base64=b64encode(rendered.png).decode("ascii"),
            overflow=rendered.metadata is True,
        )

    async def _logo_files(self, company_id: UUID) -> dict[str, bytes]:
        stored_profile = await self.company_repository.get_kp_profile(company_id)
        logo = stored_profile.logo_stored_file if stored_profile else None
        if logo is None:
            return {}
        suffix = LOGO_SUFFIXES.get(logo.mime_type, ".png")
        content = await self.storage_service.download_bytes(logo.storage_key)
        return {f"logo{suffix}": content}
