from base64 import b64encode
from collections.abc import Mapping, Sequence
from datetime import date
from uuid import UUID, uuid4

from app.core.auth_context import (
    require_admin_user,
    require_company_profile_user,
    require_staff_user,
)
from app.core.exceptions import (
    BookletBackgroundRejected,
    CompanyNotFound,
    KpEventNotFound,
)
from app.core.rich_text import rich_text_blocks
from app.models.company import Company, KpCompanyLanguage
from app.models.industry import Industry
from app.models.kp_event import INACTIVE_BOOKING_STATUSES, KpEvent, KpEventBooking
from app.models.storage import StoredFile
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.kp_repository import KpRepository
from app.schemas.company import (
    BookletBackgroundResult,
    BookletPageResult,
    CompanyProfileFields,
    UpdateCompanyProfileInput,
)
from app.services.pdf_service import PdfService, PdfUnreadable
from app.services.storage_service import StorageService, UploadKind, UploadStream

COMPANY_PAGE_TEMPLATE = "company_page.typ"
BACKGROUND_FILE = "background.pdf"
BACKGROUND_CONTEXT = "booklet_background"
BOOKLET_BACKGROUND_MAX_BYTES = 900 * 1024
A5_WIDTH_MM = 148
A5_HEIGHT_MM = 210
PAGE_SIZE_TOLERANCE_MM = 2
PDF_SIGNATURE = b"%PDF-"
SAMPLE_COMPANY_NAME = "Beispiel AG"
SAMPLE_ZONE_COLOR = "#4b5563"
SAMPLE_PAGE = {
    "company": SAMPLE_COMPANY_NAME,
    "brand_name": "Beispiel Robotics",
    "description_blocks": rich_text_blocks(
        "<p>Wir entwickeln <strong>autonome Roboter</strong> für Logistik und "
        "Industrie. Studierende arbeiten bei uns an echten Produkten, von der "
        "ersten Skizze bis zum Einsatz beim Kunden.</p>"
        "<p>We build <em>autonomous robots</em> for logistics and industry. "
        "Students work on real products with us, from the first sketch to the "
        "deployment at our customers.</p>"
    ),
    "website": "https://beispiel.example",
    "general_email": "jobs@beispiel.example",
    "general_phone": "+41 44 000 00 00",
    "places_of_work": "Zürich, Lausanne",
    "languages": ["English", "German"],
    "industries": ["Robotics", "Software"],
    "employee_count_worldwide": 420,
    "employee_count_switzerland": 120,
    "offers": {
        "internships": True,
        "part_time": True,
        "theses": True,
        "graduate_positions": False,
    },
    "logo_path": None,
    "zone_color": SAMPLE_ZONE_COLOR,
    "booth_number": "12",
}
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
        booking = upcoming_booking(bookings, date.today())
        event = (
            booking.event
            if booking is not None
            else await self.kp_repository.get_latest_kp()
        )
        files = await self._logo_files(company_id)
        entry = company_page_entry(
            company, profile, industries, booking, next(iter(files), None)
        )
        return await self._render(entry, files, await self._background_bytes(event))

    async def _render(
        self,
        entry: Mapping[str, object],
        files: dict[str, bytes],
        background: bytes | None,
    ) -> BookletPageResult:
        page_files = (
            files if background is None else {**files, BACKGROUND_FILE: background}
        )
        rendered = await self.pdf_service.render_png(
            template_name=COMPANY_PAGE_TEMPLATE,
            data={
                **entry,
                "background_path": None if background is None else BACKGROUND_FILE,
            },
            files=page_files,
            metadata_label=OVERFLOW_LABEL,
        )
        return BookletPageResult(
            png_base64=b64encode(rendered.png).decode("ascii"),
            overflow=rendered.metadata is True,
        )

    async def _get_event(self, event_id: UUID) -> KpEvent:
        event = await self.kp_repository.get_by_id(event_id)
        if event is None:
            raise KpEventNotFound(f"{BACKGROUND_CONTEXT}:{event_id}")
        return event

    async def _background_file(self, event: KpEvent | None) -> StoredFile | None:
        if event is None or event.booklet_background_stored_file_id is None:
            return None
        return await self.kp_repository.get_stored_file(
            event.booklet_background_stored_file_id
        )

    async def _background_bytes(self, event: KpEvent | None) -> bytes | None:
        stored_file = await self._background_file(event)
        if stored_file is None:
            return None
        return await self.storage_service.download_bytes(stored_file.storage_key)

    async def _background_result(
        self, stored_file: StoredFile
    ) -> BookletBackgroundResult:
        return BookletBackgroundResult(
            filename=stored_file.original_filename,
            size_bytes=stored_file.size_bytes,
            download_url=await self.storage_service.generate_download_url(
                stored_file.storage_key, stored_file.original_filename
            ),
        )

    async def get_booklet_background(
        self, event_id: UUID
    ) -> BookletBackgroundResult | None:
        require_admin_user(self.current_user)
        stored_file = await self._background_file(await self._get_event(event_id))
        if stored_file is None:
            return None
        return await self._background_result(stored_file)

    async def preview_booklet_sample(self, event_id: UUID) -> BookletPageResult:
        require_admin_user(self.current_user)
        event = await self._get_event(event_id)
        return await self._render(SAMPLE_PAGE, {}, await self._background_bytes(event))

    async def upload_booklet_background(
        self,
        event_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
    ) -> BookletBackgroundResult:
        require_admin_user(self.current_user)
        event = await self._get_event(event_id)
        content = await self._read_background(event_id, upload, content_length)
        await self._validate_background(event_id, content)
        stored_object = await self.storage_service.upload_bytes(
            key=f"kp/events/{event_id}/booklet/background/{uuid4()}.pdf",
            content=content,
            filename=filename,
            content_type="application/pdf",
        )
        previous_id = event.booklet_background_stored_file_id
        try:
            stored_file = await self.kp_repository.upsert_stored_file(
                storage_key=stored_object.key,
                original_filename=filename,
                mime_type=stored_object.mime_type,
                size_bytes=stored_object.size_bytes,
                sha256=stored_object.sha256,
                etag=stored_object.etag,
            )
            await self.kp_repository.set_booklet_background(event, stored_file.id)
        except Exception:
            await self.storage_service.delete_object(stored_object.key)
            raise
        await self._release_background(previous_id)
        return await self._background_result(stored_file)

    async def reset_booklet_background(self, event_id: UUID) -> None:
        require_admin_user(self.current_user)
        event = await self._get_event(event_id)
        previous_id = event.booklet_background_stored_file_id
        if previous_id is None:
            return
        await self.kp_repository.set_booklet_background(event, None)
        await self._release_background(previous_id)

    async def _release_background(self, stored_file_id: UUID | None) -> None:
        if stored_file_id is None:
            return
        if await self.kp_repository.count_events_with_booklet_background(
            stored_file_id
        ):
            return
        stored_file = await self.kp_repository.get_stored_file(stored_file_id)
        if stored_file is None:
            return
        await self.storage_service.delete_object(stored_file.storage_key)
        await self.kp_repository.delete_stored_file(stored_file)

    async def _read_background(
        self, event_id: UUID, upload: UploadStream, content_length: int | None
    ) -> bytes:
        identifier = f"{BACKGROUND_CONTEXT}:{event_id}"
        if content_length is not None and content_length > BOOKLET_BACKGROUND_MAX_BYTES:
            raise BookletBackgroundRejected("too_large", identifier)
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=UploadKind.PDF,
            error_context=BACKGROUND_CONTEXT,
        )
        if len(content) > BOOKLET_BACKGROUND_MAX_BYTES:
            raise BookletBackgroundRejected("too_large", identifier)
        return content

    async def _validate_background(self, event_id: UUID, content: bytes) -> None:
        identifier = f"{BACKGROUND_CONTEXT}:{event_id}"
        if not content.startswith(PDF_SIGNATURE):
            raise BookletBackgroundRejected("not_pdf", identifier)
        try:
            page = await self.pdf_service.inspect_pdf(content)
        except PdfUnreadable:
            raise BookletBackgroundRejected("unreadable", identifier) from None
        if page.has_more_pages:
            raise BookletBackgroundRejected("page_count", identifier)
        if (
            abs(page.width_mm - A5_WIDTH_MM) > PAGE_SIZE_TOLERANCE_MM
            or abs(page.height_mm - A5_HEIGHT_MM) > PAGE_SIZE_TOLERANCE_MM
        ):
            raise BookletBackgroundRejected(
                "page_size",
                identifier,
                {"widthMm": round(page.width_mm), "heightMm": round(page.height_mm)},
            )
        try:
            await self._render(SAMPLE_PAGE, {}, content)
        except Exception:
            raise BookletBackgroundRejected("unreadable", identifier) from None

    async def _logo_files(self, company_id: UUID) -> dict[str, bytes]:
        stored_profile = await self.company_repository.get_kp_profile(company_id)
        logo = stored_profile.logo_stored_file if stored_profile else None
        if logo is None:
            return {}
        suffix = LOGO_SUFFIXES.get(logo.mime_type, ".png")
        content = await self.storage_service.download_bytes(logo.storage_key)
        return {f"logo{suffix}": content}
