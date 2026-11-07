from collections.abc import Sequence
from uuid import UUID

from app.core.auth_context import (
    require_confirmed_company_user,
    require_kp_president_user,
    require_staff_user,
)
from app.core.exceptions import (
    KpBoothZoneColorExists,
    KpBoothZoneInUse,
    KpBoothZoneNameExists,
    KpBoothZoneNotFound,
    KpBoothZoneOrderInvalid,
    KpIncludedExceedsMax,
    KpIncludedServiceDuplicate,
)
from app.models.kp_event import KpEvent, KpEventBoothZone
from app.schemas.kp import (
    BoothZoneWithAvailabilityResult,
    CreateBoothZoneInput,
    IncludedServiceInput,
    StaffBoothZoneResponse,
    UpdateBoothZoneInput,
)
from app.services.booth_zone_view import booth_zones_with_availability
from app.services.kp_service.responses import ResponsesMixin
from app.services.registration_exceptions import has_registration_exception
from app.services.storage_service import UploadKind, UploadStream

LAYOUT_FILE_CONTEXT = "booth_zone_layout"


class ZonesMixin(ResponsesMixin):
    async def _get_booth_zone(self, booth_zone_id: UUID) -> KpEventBoothZone:
        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(f"booth_zone:not_found:{booth_zone_id}")
        return zone

    async def list_booth_zones(self, event_id: UUID) -> list[StaffBoothZoneResponse]:
        require_staff_user(self.current_user)
        await self._get_event(event_id)
        zones = await self.kp_repository.list_booth_zones(event_id)
        return [await self._build_staff_booth_zone_response(zone) for zone in zones]

    async def list_booth_zones_for_company(
        self, event_id: UUID
    ) -> list[BoothZoneWithAvailabilityResult]:
        user = require_confirmed_company_user(self.current_user).user
        await self._get_event(event_id)
        zones = await booth_zones_with_availability(
            self.kp_repository, self.download_urls, event_id
        )
        if user.company_id is None or not await has_registration_exception(
            self.kp_repository, event_id, user.company_id
        ):
            return zones
        return [zone.model_copy(update={"registration_open": True}) for zone in zones]

    async def _ensure_included_services_fit(
        self,
        event_id: UUID,
        context: str,
        included_services: Sequence[IncludedServiceInput],
    ) -> None:
        seen: set[UUID] = set()
        for included_service in included_services:
            service_id = included_service.service_id
            if service_id in seen:
                raise KpIncludedServiceDuplicate(f"{context}:duplicate:{service_id}")
            seen.add(service_id)
            service = await self._related_service(event_id, service_id, context)
            if included_service.included_quantity > service.max_quantity_per_booking:
                raise KpIncludedExceedsMax(
                    f"{context}:included_exceeds_max:{service_id}:"
                    f"{included_service.included_quantity}"
                )

    async def _ensure_booth_zone_identity_free(
        self,
        event_id: UUID,
        context: str,
        name: str | None,
        color: str | None,
        current_id: UUID | None = None,
    ) -> None:
        if name is not None:
            by_name = await self.kp_repository.get_booth_zone_by_name(event_id, name)
            if by_name is not None and by_name.id != current_id:
                raise KpBoothZoneNameExists(f"{context}:name:{event_id}:{name}")
        if color is not None:
            by_color = await self.kp_repository.get_booth_zone_by_color(event_id, color)
            if by_color is not None and by_color.id != current_id:
                raise KpBoothZoneColorExists(f"{context}:color:{event_id}:{color}")

    async def create_booth_zone(
        self, event_id: UUID, create_booth_zone_input: CreateBoothZoneInput
    ) -> StaffBoothZoneResponse:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        await self._ensure_booth_zone_identity_free(
            event_id,
            "create_booth_zone",
            create_booth_zone_input.name,
            create_booth_zone_input.color,
        )
        await self._ensure_included_services_fit(
            event_id, "create_booth_zone", create_booth_zone_input.included_services
        )
        zone = await self.kp_repository.create_booth_zone(
            event_id, create_booth_zone_input
        )
        return await self._build_staff_booth_zone_response(zone)

    async def reorder_booth_zones(
        self, event_id: UUID, booth_zone_ids: Sequence[UUID]
    ) -> list[StaffBoothZoneResponse]:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        zones = {
            zone.id: zone
            for zone in await self.kp_repository.list_booth_zones(event_id)
        }
        if len(booth_zone_ids) != len(zones) or set(booth_zone_ids) != set(zones):
            raise KpBoothZoneOrderInvalid(f"reorder_booth_zones:{event_id}")
        reordered = await self.kp_repository.reorder_booth_zones(
            event_id, [zones[zone_id] for zone_id in booth_zone_ids]
        )
        return [await self._build_staff_booth_zone_response(zone) for zone in reordered]

    async def update_booth_zone(
        self, booth_zone_id: UUID, update_booth_zone_input: UpdateBoothZoneInput
    ) -> StaffBoothZoneResponse:
        require_kp_president_user(self.current_user)
        zone = await self._get_booth_zone(booth_zone_id)
        updates = update_booth_zone_input.model_dump(exclude_unset=True)
        new_name = updates.get("name")
        new_color = updates.get("color")
        await self._ensure_booth_zone_identity_free(
            zone.event_id,
            "update_booth_zone",
            new_name if new_name != zone.name else None,
            new_color if new_color != zone.color else None,
            zone.id,
        )
        if update_booth_zone_input.included_services is not None:
            await self._ensure_included_services_fit(
                zone.event_id,
                "update_booth_zone",
                update_booth_zone_input.included_services,
            )
        previous_capacity = zone.capacity
        updated = await self.kp_repository.update_booth_zone(
            zone, update_booth_zone_input
        )
        if updated.capacity > previous_capacity:
            await self._promote_waitlist(updated.event_id, updated.id)
        return await self._build_staff_booth_zone_response(updated)

    async def delete_booth_zone(self, booth_zone_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        zone = await self._get_booth_zone(booth_zone_id)
        await self.kp_repository.lock_model_by_id(KpEvent, zone.event_id)
        active_bookings = await self.kp_repository.count_active_bookings_for_zone(
            zone.event_id, zone.id
        )
        if active_bookings > 0:
            raise KpBoothZoneInUse(
                f"delete_booth_zone:in_use:{booth_zone_id}:{active_bookings}"
            )
        stored_file = zone.layout_stored_file
        await self.kp_repository.delete_booth_zone(zone)
        await self.stored_files.discard(stored_file)

    async def upload_booth_zone_layout_file(
        self,
        booth_zone_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> StaffBoothZoneResponse:
        require_kp_president_user(self.current_user)
        zone = await self._get_booth_zone(booth_zone_id)
        error_context = f"{LAYOUT_FILE_CONTEXT}:{booth_zone_id}"
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=UploadKind.PDF,
            error_context=error_context,
        )
        mime_type = self.storage_service.validate_image_or_pdf_file(
            filename,
            content,
            content_type,
            error_context=error_context,
        )
        old_stored_file = zone.layout_stored_file
        updated = await self.stored_files.save(
            f"kp/booth-zones/{booth_zone_id}/layout",
            filename,
            content,
            mime_type,
            lambda stored_file: self.kp_repository.set_booth_zone_layout_stored_file_id(
                zone, stored_file.id
            ),
        )
        await self.stored_files.discard(old_stored_file)
        return await self._build_staff_booth_zone_response(updated)

    async def delete_booth_zone_layout_file(
        self, booth_zone_id: UUID
    ) -> StaffBoothZoneResponse:
        require_kp_president_user(self.current_user)
        zone = await self._get_booth_zone(booth_zone_id)
        stored_file = zone.layout_stored_file
        if stored_file is None:
            return await self._build_staff_booth_zone_response(zone)
        updated = await self.kp_repository.set_booth_zone_layout_stored_file_id(
            zone, None
        )
        await self.stored_files.discard(stored_file)
        return await self._build_staff_booth_zone_response(updated)
