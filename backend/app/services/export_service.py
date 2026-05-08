import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.decorators import require_staff
from app.core.exceptions import (
    KpBookingNotFound,
    KpEventNotFound,
    KpExportBackgroundNotFound,
    KpExportEmpty,
    KpNameTagNotFound,
    StorageFileInvalidMimeType,
    StorageFileTooLarge,
)
from app.models.kp_event import (
    KpEvent,
    KpEventBooking,
    KpEventNametagBackground,
    NameTag,
)
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.schemas.kp import (
    NametagExportCompanyResult,
    NametagExportPersonResult,
    NametagExportTargetsResult,
)
from app.services.csv_service import CsvService
from app.services.pdf_service import PdfService
from app.services.storage_service import StorageService

NAMETAG_BACKGROUND_MIME_TYPES = {"image/png", "image/jpeg"}
BOOKING_EXPORT_FIELDS = [
    "booking_id",
    "company",
    "status",
    "zone",
    "booth_number",
    "booth_size_m2",
    "base_price",
    "services",
    "nametag_count",
]
WAITLIST_EXPORT_FIELDS = [
    "company",
    "booking_id",
    "status",
    "current_zone",
    "current_booth_number",
    "target_zone",
    "priority_rank",
]
BOOKED_SERVICE_EXPORT_FIELDS = [
    "company",
    "booking_id",
    "zone",
    "booth_number",
    "service",
    "quantity",
    "included_quantity",
    "charged_quantity",
    "unit_price",
    "total_charged_price",
]
NAMETAG_DATA_EXPORT_FIELDS = [
    "name_tag_id",
    "booking_id",
    "company",
    "first_name",
    "last_name",
    "position",
]
COMPANY_DETAILS_EXPORT_FIELDS = [
    "company",
    "booking_id",
    "zone",
    "booth_number",
    "brand_name",
    "address",
    "contact_person",
    "places_of_work",
    "employees_count",
    "employees_count_switzerland",
    "offer_internship",
    "offer_part_time",
    "offer_thesis",
    "languages",
    "profile",
]
SERVICE_REQUIREMENT_EXPORT_FIELDS = [
    "company",
    "booking_id",
    "zone",
    "booth_number",
    "service",
    "requirement",
    "requirement_type",
    "uploaded",
    "filename",
    "mime_type",
    "uploaded_at",
]
BOOTH_ZONE_CAPACITY_EXPORT_FIELDS = [
    "zone",
    "capacity",
    "booked_count",
    "remaining_capacity",
    "waitlist_demand",
    "booth_size_m2",
    "base_price",
]
CONTACT_EXPORT_FIELDS = [
    "company",
    "booking_id",
    "contact_email",
    "kp_contact_user_email",
    "kp_contact_user_first_name",
    "kp_contact_user_last_name",
    "invoice_address",
    "shipping_address",
    "company_user_emails",
]
REGISTRATION_EXCEPTION_EXPORT_FIELDS = [
    "company",
    "company_id",
    "allowed_until",
]


@dataclass
class RenderedExport:
    content: bytes
    filename: str


class ExportService:
    def __init__(
        self,
        kp_repository: KpRepository,
        storage_service: StorageService,
        pdf_service: PdfService,
        csv_service: CsvService,
        current_user: User,
    ) -> None:
        self.kp_repository = kp_repository
        self.storage_service = storage_service
        self.pdf_service = pdf_service
        self.csv_service = csv_service
        self.current_user = current_user
        self.settings = get_settings()

    def _safe_filename_part(self, value: str) -> str:
        safe = "".join(
            character if character.isalnum() or character in {"-", "_"} else "-"
            for character in value.strip().lower()
        )
        return "-".join(part for part in safe.split("-") if part) or "export"

    def _bool(self, value: bool) -> str:
        return "yes" if value else "no"

    def _money(self, cents: int) -> str:
        return f"{cents / 100:.2f}"

    def _languages(self, languages: Sequence[str]) -> str:
        return ", ".join(str(language) for language in languages)

    async def _get_event_or_raise(self, event_id: UUID) -> KpEvent:
        event = await self.kp_repository.get_by_id(event_id)
        if event is None:
            raise KpEventNotFound(f"export:event_not_found:{event_id}")
        return event

    async def _list_event_bookings(
        self, event_id: UUID
    ) -> tuple[KpEvent, Sequence[KpEventBooking]]:
        event = await self._get_event_or_raise(event_id)
        return event, await self.kp_repository.list_bookings_for_event(event_id)

    def _booking_services_summary(self, booking: KpEventBooking) -> str:
        return "; ".join(
            f"{booking_service.service.name} x{booking_service.quantity}"
            for booking_service in booking.services
        )

    def _booking_row(self, booking: KpEventBooking) -> dict[str, object]:
        return {
            "booking_id": booking.id,
            "company": booking.company.name,
            "status": booking.status.value,
            "zone": booking.booth_zone.name,
            "booth_number": booking.booth_nr,
            "booth_size_m2": booking.booth_zone.booth_size,
            "base_price": self._money(booking.booth_zone.base_price),
            "services": self._booking_services_summary(booking),
            "nametag_count": len(booking.name_tags),
        }

    def _csv_export(
        self,
        rows: list[dict[str, object]],
        filename: str,
        fieldnames: list[str] | None = None,
    ) -> RenderedExport:
        content, rendered_filename = self.csv_service.render_csv(
            rows, filename, fieldnames
        )
        return RenderedExport(content, rendered_filename)

    def _validate_background_upload(
        self, filename: str, content: bytes, content_type: str | None
    ) -> str:
        mime_type = self.storage_service._normalize_mime_type(filename, content_type)
        if mime_type not in NAMETAG_BACKGROUND_MIME_TYPES:
            raise StorageFileInvalidMimeType(f"nametag_background:image:{mime_type}")
        if len(content) > self.settings.STORAGE_IMAGE_MAX_SIZE_BYTES:
            raise StorageFileTooLarge(f"nametag_background:size:{len(content)}")
        if mime_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise StorageFileInvalidMimeType("nametag_background:not_png")
        if mime_type == "image/jpeg" and not content.startswith(b"\xff\xd8"):
            raise StorageFileInvalidMimeType("nametag_background:not_jpeg")
        return mime_type

    def _background_suffix(self, mime_type: str) -> str:
        return ".jpg" if mime_type == "image/jpeg" else ".png"

    async def _get_background_bytes(
        self, event_id: UUID
    ) -> tuple[bytes, KpEventNametagBackground]:
        background = await self.kp_repository.get_nametag_background(event_id)
        if background is None:
            raise KpExportBackgroundNotFound(f"nametag_background:not_found:{event_id}")
        content = await self.storage_service.download_bytes(
            background.stored_file.storage_key
        )
        return content, background

    def _name_tag_data(self, name_tag: NameTag) -> dict[str, str]:
        return {
            "full_name": f"{name_tag.first_name} {name_tag.last_name}",
            "position": name_tag.position,
            "company": name_tag.booking.company.name,
        }

    async def _render_nametags_pdf(
        self,
        background_bytes: bytes,
        background_mime_type: str,
        name_tags: Sequence[NameTag],
        filename: str,
        columns: int | None,
    ) -> RenderedExport:
        if not name_tags:
            raise KpExportEmpty("nametag_export:empty")

        suffix = self._background_suffix(background_mime_type)
        with tempfile.NamedTemporaryFile(suffix=suffix) as background_file:
            background_file.write(background_bytes)
            background_file.flush()
            content, rendered_filename = await self.pdf_service.render(
                "exports/nametag.typ",
                {
                    "background_path": str(Path(background_file.name).resolve()),
                    "columns": columns or 2,
                    "tags": [self._name_tag_data(name_tag) for name_tag in name_tags],
                },
                filename,
                root="/",
            )

        if content is None:
            raise KpExportEmpty("nametag_export:rendering_failed")

        return RenderedExport(content, rendered_filename)

    @require_staff
    async def upload_nametag_background(
        self,
        event_id: UUID,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> KpEventNametagBackground:
        event = await self.kp_repository.get_by_id(event_id)
        if event is None:
            raise KpEventNotFound(f"nametag_background:event_not_found:{event_id}")
        mime_type = self._validate_background_upload(filename, content, content_type)
        existing_background = await self.kp_repository.get_nametag_background(event_id)
        old_storage_key = (
            existing_background.stored_file.storage_key
            if existing_background is not None
            else None
        )
        suffix = self._background_suffix(mime_type)
        storage_key = (
            f"kp/events/{event_id}/exports/nametag-background/{uuid4()}{suffix}"
        )
        stored_object = await self.storage_service.upload_bytes(
            key=storage_key,
            content=content,
            filename=filename,
            content_type=mime_type,
        )
        try:
            stored_file = await self.kp_repository.upsert_stored_file(
                storage_key=stored_object.key,
                original_filename=filename,
                mime_type=stored_object.mime_type,
                size_bytes=stored_object.size_bytes,
                sha256=stored_object.sha256,
                etag=stored_object.etag,
                stored_file=existing_background.stored_file
                if existing_background is not None
                else None,
            )
            background = await self.kp_repository.upsert_nametag_background(
                event_id=event_id,
                stored_file_id=stored_file.id,
            )
        except Exception:
            await self.storage_service.delete_object(stored_object.key)
            raise
        if old_storage_key is not None and old_storage_key != stored_object.key:
            await self.storage_service.delete_object(old_storage_key)
        return background

    @require_staff
    async def get_nametag_background(
        self, event_id: UUID
    ) -> KpEventNametagBackground | None:
        return await self.kp_repository.get_nametag_background(event_id)

    @require_staff
    async def list_nametag_export_targets(
        self, event_id: UUID
    ) -> NametagExportTargetsResult:
        await self._get_event_or_raise(event_id)
        bookings = await self.kp_repository.list_bookings_for_event(event_id)
        companies = [
            NametagExportCompanyResult(
                booking_id=booking.id,
                company_id=booking.company_id,
                company_name=booking.company.name,
                booth_zone_name=booking.booth_zone.name,
                booth_nr=booking.booth_nr,
                nametag_count=len(booking.name_tags),
            )
            for booking in bookings
            if booking.name_tags
        ]
        companies.sort(
            key=lambda company: (
                company.company_name.casefold(),
                company.booth_zone_name.casefold(),
                company.booth_nr,
            )
        )

        people = [
            NametagExportPersonResult(
                id=name_tag.id,
                booking_id=booking.id,
                company_name=booking.company.name,
                first_name=name_tag.first_name,
                last_name=name_tag.last_name,
                position=name_tag.position,
            )
            for booking in bookings
            for name_tag in booking.name_tags
        ]
        people.sort(
            key=lambda person: (
                person.company_name.casefold(),
                person.last_name.casefold(),
                person.first_name.casefold(),
            )
        )
        return NametagExportTargetsResult(companies=companies, people=people)

    @require_staff
    async def render_event_nametags(
        self, event_id: UUID, columns: int | None = None
    ) -> RenderedExport:
        event = await self.kp_repository.get_by_id(event_id)
        if event is None:
            raise KpEventNotFound(f"nametag_export:event_not_found:{event_id}")
        background_bytes, background = await self._get_background_bytes(event_id)
        name_tags = await self.kp_repository.list_name_tags_for_event(event_id)
        return await self._render_nametags_pdf(
            background_bytes,
            background.stored_file.mime_type,
            name_tags,
            f"{event.name}-nametags.pdf",
            columns,
        )

    @require_staff
    async def render_booking_nametags(
        self, booking_id: UUID, columns: int | None = None
    ) -> RenderedExport:
        booking = await self.kp_repository.get_booking_by_id(booking_id)
        if booking is None:
            raise KpBookingNotFound(f"nametag_export:booking_not_found:{booking_id}")
        background_bytes, background = await self._get_background_bytes(
            booking.event_id
        )
        name_tags = await self.kp_repository.list_name_tags_for_booking(booking_id)
        filename = f"{booking.event.name}-{booking.company.name}-nametags.pdf"
        return await self._render_nametags_pdf(
            background_bytes,
            background.stored_file.mime_type,
            name_tags,
            filename,
            columns,
        )

    @require_staff
    async def render_single_nametag(self, name_tag_id: UUID) -> RenderedExport:
        name_tag = await self.kp_repository.get_name_tag_by_id(name_tag_id)
        if name_tag is None:
            raise KpNameTagNotFound(f"nametag_export:not_found:{name_tag_id}")
        background_bytes, background = await self._get_background_bytes(
            name_tag.booking.event_id
        )
        filename = (
            f"{name_tag.booking.event.name}-{name_tag.first_name}-"
            f"{name_tag.last_name}-nametag.pdf"
        )
        return await self._render_nametags_pdf(
            background_bytes,
            background.stored_file.mime_type,
            [name_tag],
            filename,
            1,
        )

    @require_staff
    async def export_bookings_csv(self, event_id: UUID) -> RenderedExport:
        event, bookings = await self._list_event_bookings(event_id)
        rows = [self._booking_row(booking) for booking in bookings]
        return self._csv_export(
            rows, f"{event.name}-bookings-all.csv", BOOKING_EXPORT_FIELDS
        )

    @require_staff
    async def export_bookings_by_zone_zip(self, event_id: UUID) -> RenderedExport:
        event, bookings = await self._list_event_bookings(event_id)
        zones = await self.kp_repository.list_booth_zones(event_id)
        files: list[tuple[str, bytes]] = []
        for zone in zones:
            rows = [
                self._booking_row(booking)
                for booking in bookings
                if booking.booth_zone_id == zone.id
            ]
            content, filename = self.csv_service.render_csv(
                rows,
                f"{self._safe_filename_part(zone.name)}.csv",
                BOOKING_EXPORT_FIELDS,
            )
            files.append((filename, content))
        content, filename = self.csv_service.render_zip(
            files, f"{event.name}-bookings-by-zone.zip"
        )
        return RenderedExport(content, filename)

    @require_staff
    async def export_waitlist_companies_csv(self, event_id: UUID) -> RenderedExport:
        event, bookings = await self._list_event_bookings(event_id)
        rows: list[dict[str, object]] = []
        for booking in bookings:
            for entry in booking.upgrade_waitlist_entries:
                rows.append(
                    {
                        "company": booking.company.name,
                        "booking_id": booking.id,
                        "status": booking.status.value,
                        "current_zone": booking.booth_zone.name,
                        "current_booth_number": booking.booth_nr,
                        "target_zone": entry.target_booth_zone.name,
                        "priority_rank": entry.priority_rank or "",
                    }
                )
        return self._csv_export(
            rows, f"{event.name}-waitlist-companies.csv", WAITLIST_EXPORT_FIELDS
        )

    @require_staff
    async def export_booked_services_csv(self, event_id: UUID) -> RenderedExport:
        event, bookings = await self._list_event_bookings(event_id)
        rows: list[dict[str, object]] = []
        for booking in bookings:
            for booking_service in booking.services:
                rows.append(
                    {
                        "company": booking.company.name,
                        "booking_id": booking.id,
                        "zone": booking.booth_zone.name,
                        "booth_number": booking.booth_nr,
                        "service": booking_service.service.name,
                        "quantity": booking_service.quantity,
                        "included_quantity": booking_service.included_quantity,
                        "charged_quantity": booking_service.charged_quantity,
                        "unit_price": self._money(booking_service.service.price),
                        "total_charged_price": self._money(
                            booking_service.charged_quantity
                            * booking_service.service.price
                        ),
                    }
                )
        return self._csv_export(
            rows, f"{event.name}-booked-services.csv", BOOKED_SERVICE_EXPORT_FIELDS
        )

    @require_staff
    async def export_nametags_data_csv(self, event_id: UUID) -> RenderedExport:
        event = await self._get_event_or_raise(event_id)
        name_tags = await self.kp_repository.list_name_tags_for_event(event_id)
        rows: list[dict[str, object]] = [
            {
                "name_tag_id": name_tag.id,
                "booking_id": name_tag.booking_id,
                "company": name_tag.booking.company.name,
                "first_name": name_tag.first_name,
                "last_name": name_tag.last_name,
                "position": name_tag.position,
            }
            for name_tag in name_tags
        ]
        return self._csv_export(
            rows, f"{event.name}-nametags-data.csv", NAMETAG_DATA_EXPORT_FIELDS
        )

    @require_staff
    async def export_company_details_csv(self, event_id: UUID) -> RenderedExport:
        event, bookings = await self._list_event_bookings(event_id)
        rows: list[dict[str, object]] = []
        for booking in bookings:
            details = booking.company_details
            rows.append(
                {
                    "company": booking.company.name,
                    "booking_id": booking.id,
                    "zone": booking.booth_zone.name,
                    "booth_number": booking.booth_nr,
                    "brand_name": details.brand_name if details else "",
                    "address": details.address if details else "",
                    "contact_person": details.contact_person if details else "",
                    "places_of_work": details.places_of_work if details else "",
                    "employees_count": details.employees_count if details else "",
                    "employees_count_switzerland": details.employees_count_switzerland
                    if details
                    else "",
                    "offer_internship": self._bool(details.offer_internship)
                    if details
                    else "",
                    "offer_part_time": self._bool(details.offer_part_time)
                    if details
                    else "",
                    "offer_thesis": self._bool(details.offer_thesis) if details else "",
                    "languages": self._languages(details.languages) if details else "",
                    "profile": details.profile if details else "",
                }
            )
        return self._csv_export(
            rows, f"{event.name}-company-details.csv", COMPANY_DETAILS_EXPORT_FIELDS
        )

    @require_staff
    async def export_service_requirements_csv(self, event_id: UUID) -> RenderedExport:
        event, bookings = await self._list_event_bookings(event_id)
        rows: list[dict[str, object]] = []
        for booking in bookings:
            for booking_service in booking.services:
                files_by_requirement = {
                    file_link.requirement_id: file_link
                    for file_link in booking_service.requirement_file_links
                }
                for requirement in booking_service.service.requirements:
                    file_link = files_by_requirement.get(requirement.id)
                    stored_file = file_link.stored_file if file_link else None
                    rows.append(
                        {
                            "company": booking.company.name,
                            "booking_id": booking.id,
                            "zone": booking.booth_zone.name,
                            "booth_number": booking.booth_nr,
                            "service": booking_service.service.name,
                            "requirement": requirement.name,
                            "requirement_type": requirement.type.value,
                            "uploaded": self._bool(stored_file is not None),
                            "filename": stored_file.original_filename
                            if stored_file
                            else "",
                            "mime_type": stored_file.mime_type if stored_file else "",
                            "uploaded_at": stored_file.created_at.isoformat()
                            if stored_file
                            else "",
                        }
                    )
        return self._csv_export(
            rows,
            f"{event.name}-service-requirements-status.csv",
            SERVICE_REQUIREMENT_EXPORT_FIELDS,
        )

    @require_staff
    async def export_booth_zone_capacity_csv(self, event_id: UUID) -> RenderedExport:
        event, bookings = await self._list_event_bookings(event_id)
        zones = await self.kp_repository.list_booth_zones(event_id)
        rows: list[dict[str, object]] = []
        for zone in zones:
            zone_bookings = [
                booking for booking in bookings if booking.booth_zone_id == zone.id
            ]
            waitlist_demand = sum(
                1
                for booking in bookings
                for entry in booking.upgrade_waitlist_entries
                if entry.target_booth_zone_id == zone.id
            )
            rows.append(
                {
                    "zone": zone.name,
                    "capacity": zone.capacity,
                    "booked_count": len(zone_bookings),
                    "remaining_capacity": max(zone.capacity - len(zone_bookings), 0),
                    "waitlist_demand": waitlist_demand,
                    "booth_size_m2": zone.booth_size,
                    "base_price": self._money(zone.base_price),
                }
            )
        return self._csv_export(
            rows,
            f"{event.name}-booth-zone-capacity.csv",
            BOOTH_ZONE_CAPACITY_EXPORT_FIELDS,
        )

    @require_staff
    async def export_contacts_csv(self, event_id: UUID) -> RenderedExport:
        event, bookings = await self._list_event_bookings(event_id)
        rows: list[dict[str, object]] = []
        for booking in bookings:
            profile = booking.company.kp_profile
            contact_user = profile.kp_contact_user if profile else None
            company_users = sorted(
                booking.company.users,
                key=lambda user: (
                    user.last_name or "",
                    user.first_name or "",
                    user.email,
                ),
            )
            rows.append(
                {
                    "company": booking.company.name,
                    "booking_id": booking.id,
                    "contact_email": profile.contact_email if profile else "",
                    "kp_contact_user_email": contact_user.email if contact_user else "",
                    "kp_contact_user_first_name": contact_user.first_name
                    if contact_user
                    else "",
                    "kp_contact_user_last_name": contact_user.last_name
                    if contact_user
                    else "",
                    "invoice_address": profile.invoice_address if profile else "",
                    "shipping_address": profile.shipping_address if profile else "",
                    "company_user_emails": ", ".join(
                        user.email for user in company_users
                    ),
                }
            )
        return self._csv_export(
            rows, f"{event.name}-contacts.csv", CONTACT_EXPORT_FIELDS
        )

    @require_staff
    async def export_registration_exceptions_csv(
        self, event_id: UUID
    ) -> RenderedExport:
        event = await self._get_event_or_raise(event_id)
        exceptions = await self.kp_repository.list_registration_exceptions(event_id)
        rows: list[dict[str, object]] = [
            {
                "company": exception.company.name,
                "company_id": exception.company_id,
                "allowed_until": exception.allowed_until.isoformat(),
            }
            for exception in exceptions
        ]
        return self._csv_export(
            rows,
            f"{event.name}-registration-exceptions.csv",
            REGISTRATION_EXCEPTION_EXPORT_FIELDS,
        )
