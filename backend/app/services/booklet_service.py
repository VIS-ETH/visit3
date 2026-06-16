import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from app.core.auth_context import (
    require_assigned_company_user,
    require_staff_user,
)
from app.core.downloads import sanitize_download_filename
from app.core.exceptions import (
    KpBookingConfirmedReadonly,
    KpBookingNotFound,
    KpBookingNotOwned,
    KpBookletAssetInvalidType,
    KpBookletExportTaskNotFound,
    KpBookletExportTaskNotReady,
    KpExportEmpty,
)
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookletAssets,
    KpEventBookletExportTask,
    KpEventBookletExportTaskStatus,
    KpEventService,
)
from app.models.storage import StoredFile
from app.models.user import User
from app.repositories.kp_repository import KpRepository
from app.schemas.kp import (
    BookletAssetsResponse,
    BookletExportTaskResponse,
    StoredFileResponse,
)
from app.services.attachment_utils import (
    delete_attached_file,
    upload_and_replace_attached_file,
)
from app.services.kp_helpers import get_event_or_raise
from app.services.pdf_service import PdfService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

BOOKLET_TEMPLATE_NAME = "booklet.typ"

BookletAssetType = Literal["intro_page", "blank_page", "missing_advertisement"]
ASSET_FIELD_NAMES: dict[BookletAssetType, str] = {
    "intro_page": "intro_page_stored_file_id",
    "blank_page": "blank_page_stored_file_id",
    "missing_advertisement": "missing_advertisement_stored_file_id",
}


@dataclass
class RenderedBooklet:
    content: bytes
    filename: str


def _to_asset_type(value: str) -> BookletAssetType:
    if value not in ASSET_FIELD_NAMES:
        raise KpBookletAssetInvalidType(f"booklet_asset:invalid_type:{value}")
    return value  # type: ignore[return-value]


class BookletService:
    def __init__(
        self,
        kp_repository: KpRepository,
        storage_service: StorageService,
        pdf_service: PdfService,
        current_user: User,
    ) -> None:
        self.kp_repository = kp_repository
        self.storage_service = storage_service
        self.pdf_service = pdf_service
        self.current_user = current_user

    # --- Helpers ---

    async def _get_event_or_raise(self, event_id: UUID) -> KpEvent:
        return await get_event_or_raise(self.kp_repository, event_id, context="booklet")

    def _stored_file_to_response(self, stored_file: StoredFile) -> StoredFileResponse:
        return StoredFileResponse(
            id=stored_file.id,
            original_filename=stored_file.original_filename,
            mime_type=stored_file.mime_type,
            size_bytes=stored_file.size_bytes,
            sha256=stored_file.sha256,
            etag=stored_file.etag,
            created_at=stored_file.created_at,
            updated_at=stored_file.updated_at,
        )

    def _assets_to_response(
        self, event_id: UUID, assets: KpEventBookletAssets | None
    ) -> BookletAssetsResponse:
        if assets is None:
            return BookletAssetsResponse(
                id=uuid4(),
                event_id=event_id,
            )
        return BookletAssetsResponse(
            id=assets.id,
            event_id=assets.event_id,
            intro_page=(
                self._stored_file_to_response(assets.intro_page_stored_file)
                if assets.intro_page_stored_file is not None
                else None
            ),
            blank_page=(
                self._stored_file_to_response(assets.blank_page_stored_file)
                if assets.blank_page_stored_file is not None
                else None
            ),
            missing_advertisement=(
                self._stored_file_to_response(assets.missing_advertisement_stored_file)
                if assets.missing_advertisement_stored_file is not None
                else None
            ),
        )

    def _task_to_response(
        self, task: KpEventBookletExportTask
    ) -> BookletExportTaskResponse:
        return BookletExportTaskResponse(
            id=task.id,
            event_id=task.event_id,
            status=task.status,
            error=task.error,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_at=task.created_at,
            output_file=(
                self._stored_file_to_response(task.output_stored_file)
                if task.output_stored_file is not None
                else None
            ),
        )

    # --- Asset CRUD (staff) ---

    async def get_assets(self, event_id: UUID) -> BookletAssetsResponse:
        require_staff_user(self.current_user)
        await self._get_event_or_raise(event_id)
        assets = await self.kp_repository.get_booklet_assets(event_id)
        return self._assets_to_response(event_id, assets)

    async def upload_asset(
        self,
        event_id: UUID,
        asset_type_value: str,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> BookletAssetsResponse:
        require_staff_user(self.current_user)
        await self._get_event_or_raise(event_id)
        asset_type = _to_asset_type(asset_type_value)
        mime_type = self.storage_service.validate_pdf_file(
            filename,
            content,
            content_type,
            error_context=f"booklet_asset:{asset_type}:{event_id}",
        )
        existing_assets = await self.kp_repository.get_booklet_assets(event_id)
        old_stored_file = (
            getattr(existing_assets, f"{asset_type}_stored_file")
            if existing_assets is not None
            else None
        )

        suffix = Path(filename).suffix or ".pdf"
        storage_key = f"kp/events/{event_id}/booklet/{asset_type}/{uuid4()}{suffix}"
        await upload_and_replace_attached_file(
            storage_service=self.storage_service,
            kp_repository=self.kp_repository,
            filename=filename,
            content=content,
            content_type=mime_type,
            storage_key=storage_key,
            old_stored_file=old_stored_file,
            attach=lambda stored_file: self.kp_repository.upsert_booklet_asset_file(
                event_id, ASSET_FIELD_NAMES[asset_type], stored_file.id
            ),
        )
        assets = await self.kp_repository.get_booklet_assets(event_id)
        return self._assets_to_response(event_id, assets)

    async def delete_asset(
        self, event_id: UUID, asset_type_value: str
    ) -> BookletAssetsResponse:
        require_staff_user(self.current_user)
        await self._get_event_or_raise(event_id)
        asset_type = _to_asset_type(asset_type_value)
        existing = await self.kp_repository.get_booklet_assets(event_id)
        if existing is None:
            return self._assets_to_response(event_id, None)
        old_stored_file = getattr(existing, f"{asset_type}_stored_file")
        if old_stored_file is None:
            return self._assets_to_response(event_id, existing)
        await delete_attached_file(
            storage_service=self.storage_service,
            kp_repository=self.kp_repository,
            old_stored_file=old_stored_file,
            detach=lambda: self.kp_repository.upsert_booklet_asset_file(
                event_id, ASSET_FIELD_NAMES[asset_type], None
            ),
        )
        assets = await self.kp_repository.get_booklet_assets(event_id)
        return self._assets_to_response(event_id, assets)

    # --- Logo upload (company-facing, lives here because it's a booklet asset) ---

    async def upload_company_logo(
        self,
        booking_id: UUID,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> StoredFileResponse:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self.kp_repository.get_booking_by_id(booking_id)
        if booking is None:
            raise KpBookingNotFound(f"company_logo:booking_not_found:{booking_id}")
        if booking.company_id != company_user.company_id:
            raise KpBookingNotOwned(f"company_logo:not_owned:{booking_id}")
        if booking.status in {KpBookingStatus.CONFIRMED, KpBookingStatus.CANCELLED}:
            raise KpBookingConfirmedReadonly(
                f"company_logo:readonly:{booking_id}:{booking.status}"
            )

        details = await self.kp_repository.get_company_details_by_booking_id(booking_id)
        if details is None:
            # Create empty company-details row so we can attach the logo.
            from app.schemas.kp import UpsertCompanyDetailsInput

            details = await self.kp_repository.upsert_company_details(
                booking_id,
                UpsertCompanyDetailsInput(),
                [],
            )

        mime_type = self.storage_service.validate_image_file(
            filename,
            content,
            content_type,
            error_context=f"company_logo:{booking_id}",
        )
        old_stored_file = details.logo_stored_file

        suffix = Path(filename).suffix or ".png"
        storage_key = f"kp/bookings/{booking_id}/logo/{uuid4()}{suffix}"
        stored_file, _ = await upload_and_replace_attached_file(
            storage_service=self.storage_service,
            kp_repository=self.kp_repository,
            filename=filename,
            content=content,
            content_type=mime_type,
            storage_key=storage_key,
            old_stored_file=old_stored_file,
            attach=lambda stored_file: self.kp_repository.set_company_details_logo_stored_file_id(
                details, stored_file.id
            ),
        )
        return self._stored_file_to_response(stored_file)

    async def delete_company_logo(self, booking_id: UUID) -> None:
        company_user = require_assigned_company_user(self.current_user)
        booking = await self.kp_repository.get_booking_by_id(booking_id)
        if booking is None:
            raise KpBookingNotFound(f"company_logo:booking_not_found:{booking_id}")
        if booking.company_id != company_user.company_id:
            raise KpBookingNotOwned(f"company_logo:not_owned:{booking_id}")
        if booking.status in {KpBookingStatus.CONFIRMED, KpBookingStatus.CANCELLED}:
            raise KpBookingConfirmedReadonly(
                f"company_logo:readonly:{booking_id}:{booking.status}"
            )
        details = await self.kp_repository.get_company_details_by_booking_id(booking_id)
        if details is None or details.logo_stored_file is None:
            return
        stored_file = details.logo_stored_file
        await delete_attached_file(
            storage_service=self.storage_service,
            kp_repository=self.kp_repository,
            old_stored_file=stored_file,
            detach=lambda: self.kp_repository.set_company_details_logo_stored_file_id(
                details, None
            ),
        )

    # --- Export tasks (staff) ---

    async def create_export_task(self, event_id: UUID) -> BookletExportTaskResponse:
        require_staff_user(self.current_user)
        await self._get_event_or_raise(event_id)
        task = await self.kp_repository.create_booklet_export_task(event_id)
        return self._task_to_response(task)

    async def list_export_tasks(
        self, event_id: UUID
    ) -> list[BookletExportTaskResponse]:
        require_staff_user(self.current_user)
        await self._get_event_or_raise(event_id)
        tasks = await self.kp_repository.list_booklet_export_tasks(event_id)
        return [self._task_to_response(task) for task in tasks]

    async def get_export_task(self, task_id: UUID) -> BookletExportTaskResponse:
        require_staff_user(self.current_user)
        task = await self.kp_repository.get_booklet_export_task(task_id)
        if task is None:
            raise KpBookletExportTaskNotFound(f"booklet_task:not_found:{task_id}")
        return self._task_to_response(task)

    async def get_export_task_download_url(self, task_id: UUID) -> str:
        require_staff_user(self.current_user)
        task = await self.kp_repository.get_booklet_export_task(task_id)
        if task is None:
            raise KpBookletExportTaskNotFound(f"booklet_task:not_found:{task_id}")
        if (
            task.status != KpEventBookletExportTaskStatus.COMPLETED
            or task.output_stored_file is None
        ):
            raise KpBookletExportTaskNotReady(f"booklet_task:not_ready:{task_id}")
        return await self.storage_service.generate_download_url(
            task.output_stored_file.storage_key,
            task.output_stored_file.original_filename,
        )

    # --- Rendering (used by the async worker) ---

    def _booklet_entry_data(self, booking: KpEventBooking) -> dict[str, object] | None:
        details = booking.company_details
        if details is None:
            return None
        offers = [
            label
            for enabled, label in [
                (details.offer_internship, "Internships"),
                (details.offer_part_time, "Part-time roles"),
                (details.offer_thesis, "Thesis topics"),
            ]
            if enabled
        ]
        return {
            "company": booking.company.name,
            "brand_name": details.brand_name or booking.company.name,
            "zone": booking.booth_zone.name,
            "zone_color": booking.booth_zone.color,
            "booth_number": booking.booth_nr or "",
            "profile": details.profile,
            "address": details.address,
            "contact_person": details.contact_person,
            "places_of_work": details.places_of_work,
            "website": details.website,
            "employees_count": details.employees_count,
            "employees_count_switzerland": details.employees_count_switzerland,
            "vacancies_worldwide": details.vacancies_worldwide,
            "vacancies_switzerland": details.vacancies_switzerland,
            "annual_revenue_chf_millions": details.annual_revenue_chf_millions,
            "languages": [str(language) for language in details.languages],
            "industries": [link.industry.name for link in details.industry_links],
            "offers": offers,
        }

    def _sort_bookings_for_booklet(
        self, bookings: Sequence[KpEventBooking]
    ) -> list[KpEventBooking]:
        def sort_key(booking: KpEventBooking) -> tuple[int, str, str, int]:
            zone = booking.booth_zone
            details = booking.company_details
            brand = (
                details.brand_name if details and details.brand_name else ""
            ) or booking.company.name
            return (
                zone.order,
                zone.name.casefold(),
                brand.casefold(),
                booking.booth_nr or 0,
            )

        return sorted(bookings, key=sort_key)

    def _zone_grouping_key(self, booking: KpEventBooking) -> tuple[int, str]:
        zone = booking.booth_zone
        return (zone.order, zone.name)

    def _booking_advertisement_file_key(
        self,
        booking: KpEventBooking,
        advertisement_service: KpEventService | None,
    ) -> str | None:
        if advertisement_service is None:
            return None
        for booking_service in booking.services:
            if booking_service.service_id != advertisement_service.id:
                continue
            for file_link in booking_service.requirement_file_links:
                stored_file = file_link.stored_file
                if (
                    stored_file is not None
                    and stored_file.mime_type == "application/pdf"
                ):
                    return stored_file.storage_key
        return None

    def _build_booklet_pages(
        self,
        entry_with_ad: Sequence[tuple[KpEventBooking, dict[str, object], str | None]],
        missing_advertisement_path: str | None,
    ) -> list[dict[str, object]]:
        """
        Visit2 layout: every page is a landscape A4 spread.
        * `pair` — portrait left + portrait right (two non-ad portraits in same zone)
        * `with_ad` — portrait left + ad right (booking has an ad, or fallback)
        * `leftover` — portrait left, blank right (odd portrait at end of zone)
        """
        pages: list[dict[str, object]] = []
        pending: dict[str, object] | None = None
        current_zone_key: tuple[int, str] | None = None

        for booking, entry, ad_filename in entry_with_ad:
            zone_key = self._zone_grouping_key(booking)
            if current_zone_key is not None and zone_key != current_zone_key:
                if pending is not None:
                    pages.append({"type": "leftover", "entry": pending})
                    pending = None
            current_zone_key = zone_key

            effective_ad = ad_filename or missing_advertisement_path
            if effective_ad is not None:
                if pending is not None:
                    pages.append({"type": "leftover", "entry": pending})
                    pending = None
                pages.append(
                    {"type": "with_ad", "entry": entry, "ad_path": effective_ad}
                )
                continue

            if pending is not None:
                pages.append(
                    {"type": "pair", "left_entry": pending, "right_entry": entry}
                )
                pending = None
            else:
                pending = entry

        if pending is not None:
            pages.append({"type": "leftover", "entry": pending})
        return pages

    async def render_booklet_pdf(self, event_id: UUID) -> RenderedBooklet:
        """
        Synchronous render path: collects all data, downloads referenced files
        into a temp workspace, and asks the typst PdfService to compile.
        Called by the async runner; not exposed as a route.
        """
        event = await self._get_event_or_raise(event_id)
        bookings = await self.kp_repository.list_bookings_for_event(event_id)
        bookings = [
            booking
            for booking in bookings
            if booking.status != KpBookingStatus.CANCELLED
        ]

        advertisement_service: KpEventService | None = None
        if event.advertisement_service_id is not None:
            advertisement_service = await self.kp_repository.get_service_by_id(
                event.advertisement_service_id
            )

        assets = await self.kp_repository.get_booklet_assets(event_id)
        sorted_bookings = self._sort_bookings_for_booklet(bookings)

        intro_page_path: str | None = None
        blank_page_path: str | None = None
        missing_ad_path: str | None = None
        entry_with_ad: list[
            tuple[KpEventBooking, dict[str, object], str | None]
        ] = []

        async def _materialize(workspace_path: Path) -> None:
            nonlocal intro_page_path, blank_page_path, missing_ad_path

            async def _download(stored_file: StoredFile, filename_hint: str) -> str:
                content = await self.storage_service.download_bytes(
                    stored_file.storage_key
                )
                local_name = f"{filename_hint}{Path(stored_file.original_filename).suffix or '.pdf'}"
                (workspace_path / local_name).write_bytes(content)
                return local_name

            if assets is not None:
                if assets.intro_page_stored_file is not None:
                    intro_page_path = await _download(
                        assets.intro_page_stored_file, "intro_page"
                    )
                if assets.blank_page_stored_file is not None:
                    blank_page_path = await _download(
                        assets.blank_page_stored_file, "blank_page"
                    )
                if assets.missing_advertisement_stored_file is not None:
                    missing_ad_path = await _download(
                        assets.missing_advertisement_stored_file,
                        "missing_advertisement",
                    )

            for booking in sorted_bookings:
                entry = self._booklet_entry_data(booking)
                if entry is None:
                    continue
                storage_key = self._booking_advertisement_file_key(
                    booking, advertisement_service
                )
                ad_filename: str | None = None
                if storage_key is not None:
                    ad_bytes = await self.storage_service.download_bytes(storage_key)
                    ad_filename = f"ad-{booking.id}.pdf"
                    (workspace_path / ad_filename).write_bytes(ad_bytes)
                entry_with_ad.append((booking, entry, ad_filename))

            if not entry_with_ad:
                raise KpExportEmpty("booklet_export:empty")

        content, rendered_filename = await self.pdf_service.render_with_workspace(
            BOOKLET_TEMPLATE_NAME,
            {
                "event_name": event.name,
                "pages": self._build_booklet_pages(entry_with_ad, missing_ad_path),
                "intro_page_path": intro_page_path,
                "blank_page_path": blank_page_path,
            },
            sanitize_download_filename(f"{event.name}-booklet.pdf"),
            materialize=_materialize,
        )
        return RenderedBooklet(content=content, filename=rendered_filename)

    # --- Persist render result on a task row ---

    async def store_rendered_booklet(
        self,
        task: KpEventBookletExportTask,
        rendered: RenderedBooklet,
    ) -> KpEventBookletExportTask:
        storage_key = f"kp/events/{task.event_id}/booklet/exports/{task.id}.pdf"
        stored_object = await self.storage_service.upload_bytes(
            key=storage_key,
            content=rendered.content,
            filename=rendered.filename,
            content_type="application/pdf",
        )
        stored_file = await self.kp_repository.upsert_stored_file(
            storage_key=stored_object.key,
            original_filename=rendered.filename,
            mime_type=stored_object.mime_type,
            size_bytes=stored_object.size_bytes,
            sha256=stored_object.sha256,
            etag=stored_object.etag,
            stored_file=None,
        )
        return await self.kp_repository.complete_booklet_export_task(
            task, stored_file.id
        )
