from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from app.core.auth_context import require_kp_president_user
from app.core.exceptions import (
    KpBoothZoneEventMismatch,
    KpBoothZoneNotFound,
    KpEventNotFound,
    KpVenueBoothNumberDuplicate,
    KpVenueLayoutNameExists,
    KpVenueLayoutNotFound,
    KpVenueOutOfBounds,
)
from app.models.kp_event import KpEvent, KpEventBoothZone
from app.models.user import User
from app.models.venue import (
    FLOOR_PLAN_SIZES,
    KpVenueBooth,
    KpVenueLayout,
    KpVenueZoneShape,
)
from app.repositories.kp_repository import KpRepository
from app.repositories.venue_repository import VenueRepository
from app.schemas.kp import (
    StoredFileResponse,
)
from app.schemas.venue import (
    CreateVenueLayoutInput,
    UpdateVenueLayoutInput,
    VenueBoothInput,
    VenueBoothResponse,
    VenueLayoutResult,
    VenueMapBoothResponse,
    VenueMapLayoutResult,
    VenueMapResult,
    VenueOwnBookingResult,
    VenuePoint,
    VenueZoneShapeInput,
    VenueZoneShapeResponse,
    shape_extent_points,
)
from app.services.booth_zone_view import (
    booth_zones_with_availability,
)
from app.services.download_urls import DownloadUrls
from app.services.storage_service import StorageService, UploadKind, UploadStream

BACKGROUND_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
BACKGROUND_CONTEXT = "venue_layout_background"


@dataclass(frozen=True)
class LayoutBounds:
    layout_id: UUID
    width: int
    height: int


def sized_to_floor_plan[LayoutInput: (CreateVenueLayoutInput, UpdateVenueLayoutInput)](
    layout_input: LayoutInput,
) -> LayoutInput:
    if layout_input.floor_plan is None:
        return layout_input
    width, height = FLOOR_PLAN_SIZES[layout_input.floor_plan]
    return layout_input.model_copy(update={"width": width, "height": height})


def layout_bounds(layout: KpVenueLayout) -> LayoutBounds:
    return LayoutBounds(layout_id=layout.id, width=layout.width, height=layout.height)


class VenueService:
    def __init__(
        self,
        venue_repository: VenueRepository,
        kp_repository: KpRepository,
        storage_service: StorageService,
        current_user: User,
    ) -> None:
        self.venue_repository = venue_repository
        self.kp_repository = kp_repository
        self.storage_service = storage_service
        self.download_urls = DownloadUrls(storage_service)
        self.current_user = current_user

    async def _get_event(self, event_id: UUID) -> KpEvent:
        event = await self.kp_repository.get_by_id(event_id)
        if event is None:
            raise KpEventNotFound(f"venue:event_not_found:{event_id}")
        return event

    async def _get_layout(self, layout_id: UUID) -> KpVenueLayout:
        layout = await self.venue_repository.get_layout_by_id(layout_id)
        if layout is None:
            raise KpVenueLayoutNotFound(f"venue_layout:not_found:{layout_id}")
        return layout

    async def _ensure_layout_name_free(
        self,
        event_id: UUID,
        context: str,
        name: str | None,
        current_id: UUID | None = None,
    ) -> None:
        if name is None:
            return
        existing = await self.venue_repository.get_layout_by_name(event_id, name)
        if existing is not None and existing.id != current_id:
            raise KpVenueLayoutNameExists(f"{context}:{event_id}:{name}")

    async def _get_event_zone(
        self, event_id: UUID, booth_zone_id: UUID, context: str
    ) -> KpEventBoothZone:
        zone = await self.kp_repository.get_booth_zone_by_id(booth_zone_id)
        if zone is None:
            raise KpBoothZoneNotFound(f"{context}:zone_not_found:{booth_zone_id}")
        if zone.event_id != event_id:
            raise KpBoothZoneEventMismatch(
                f"{context}:zone_event_mismatch:{booth_zone_id}"
            )
        return zone

    def _ensure_within_bounds(
        self, bounds: LayoutBounds, points: Sequence[VenuePoint], context: str
    ) -> None:
        for x, y in points:
            if not (0 <= x <= bounds.width and 0 <= y <= bounds.height):
                raise KpVenueOutOfBounds(f"{context}:{bounds.layout_id}:{x}:{y}")

    async def _ensure_resize_keeps_elements_inside(
        self, layout: KpVenueLayout, update: UpdateVenueLayoutInput
    ) -> None:
        updates = update.model_dump(exclude_unset=True)
        bounds = LayoutBounds(
            layout_id=layout.id,
            width=updates.get("width") or layout.width,
            height=updates.get("height") or layout.height,
        )
        if bounds.width >= layout.width and bounds.height >= layout.height:
            return
        for shape in await self.venue_repository.list_zone_shapes([layout.id]):
            response = self._shape_response(shape)
            self._ensure_within_bounds(
                bounds, shape_extent_points(response.shape), "resize_venue_layout"
            )
            if response.label_position is not None:
                self._ensure_within_bounds(
                    bounds, [response.label_position], "resize_venue_layout"
                )
        for booth in await self.venue_repository.list_booths([layout.id]):
            self._ensure_within_bounds(
                bounds, [(booth.x, booth.y)], "resize_venue_layout"
            )

    async def _background_url(self, layout: KpVenueLayout) -> str | None:
        return await self.download_urls.of(layout.background_stored_file)

    def _shape_response(self, shape: KpVenueZoneShape) -> VenueZoneShapeResponse:
        return VenueZoneShapeResponse.model_validate(
            {
                "id": shape.id,
                "layout_id": shape.layout_id,
                "booth_zone_id": shape.booth_zone_id,
                "shape": shape.shape,
                "label_position": shape.label_position,
            }
        )

    def _booth_response(self, booth: KpVenueBooth) -> VenueBoothResponse:
        return VenueBoothResponse.model_validate(booth, from_attributes=True)

    async def _build_layout(
        self,
        layout: KpVenueLayout,
        shapes: Sequence[KpVenueZoneShape],
        booths: Sequence[KpVenueBooth],
    ) -> VenueLayoutResult:
        return VenueLayoutResult(
            id=layout.id,
            event_id=layout.event_id,
            name=layout.name,
            order=layout.order,
            width=layout.width,
            height=layout.height,
            is_active=layout.is_active,
            floor_plan=layout.floor_plan,
            background_url=await self._background_url(layout),
            background_file=(
                StoredFileResponse.model_validate(
                    layout.background_stored_file, from_attributes=True
                )
                if layout.background_stored_file is not None
                else None
            ),
            zone_shapes=[self._shape_response(shape) for shape in shapes],
            booths=[self._booth_response(booth) for booth in booths],
        )

    async def _build_layouts(
        self, layouts: Sequence[KpVenueLayout]
    ) -> list[VenueLayoutResult]:
        layout_ids = [layout.id for layout in layouts]
        shapes = await self.venue_repository.list_zone_shapes(layout_ids)
        booths = await self.venue_repository.list_booths(layout_ids)
        return [
            await self._build_layout(
                layout,
                [shape for shape in shapes if shape.layout_id == layout.id],
                [booth for booth in booths if booth.layout_id == layout.id],
            )
            for layout in layouts
        ]

    async def _build_single_layout(self, layout: KpVenueLayout) -> VenueLayoutResult:
        built = await self._build_layouts([layout])
        return built[0]

    async def list_layouts(self, event_id: UUID) -> list[VenueLayoutResult]:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        return await self._build_layouts(
            await self.venue_repository.list_layouts(event_id)
        )

    async def create_layout(
        self, event_id: UUID, create_layout_input: CreateVenueLayoutInput
    ) -> VenueLayoutResult:
        require_kp_president_user(self.current_user)
        await self._get_event(event_id)
        await self._ensure_layout_name_free(
            event_id, "create_venue_layout", create_layout_input.name
        )
        layout = await self.venue_repository.create_layout(
            event_id, sized_to_floor_plan(create_layout_input)
        )
        return await self._build_single_layout(layout)

    async def update_layout(
        self, layout_id: UUID, update_layout_input: UpdateVenueLayoutInput
    ) -> VenueLayoutResult:
        require_kp_president_user(self.current_user)
        layout = await self._get_layout(layout_id)
        new_name = update_layout_input.model_dump(exclude_unset=True).get("name")
        await self._ensure_layout_name_free(
            layout.event_id,
            "update_venue_layout",
            new_name if new_name != layout.name else None,
            layout.id,
        )
        sized_update = sized_to_floor_plan(update_layout_input)
        await self._ensure_resize_keeps_elements_inside(layout, sized_update)
        updated = await self.venue_repository.update_layout(layout, sized_update)
        return await self._build_single_layout(updated)

    async def delete_layout(self, layout_id: UUID) -> None:
        require_kp_president_user(self.current_user)
        layout = await self._get_layout(layout_id)
        stored_file = layout.background_stored_file
        await self.venue_repository.delete_layout(layout)
        if stored_file is not None:
            await self.storage_service.delete_object(stored_file.storage_key)
            await self.kp_repository.delete_stored_file(stored_file)

    async def upload_background(
        self,
        layout_id: UUID,
        filename: str,
        upload: UploadStream,
        content_length: int | None,
        content_type: str | None,
    ) -> VenueLayoutResult:
        require_kp_president_user(self.current_user)
        layout = await self._get_layout(layout_id)
        error_context = f"{BACKGROUND_CONTEXT}:{layout_id}"
        content = await self.storage_service.read_upload(
            upload,
            content_length=content_length,
            kind=UploadKind.IMAGE,
            error_context=error_context,
        )
        mime_type = self.storage_service.validate_image_file(
            filename,
            content,
            content_type,
            error_context=error_context,
            allowed_mime_types=BACKGROUND_MIME_TYPES,
        )
        old_stored_file = layout.background_stored_file
        storage_key = (
            f"kp/venue-layouts/{layout_id}/background/{uuid4()}{Path(filename).suffix}"
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
                stored_file=None,
            )
            updated = await self.venue_repository.set_layout_background_stored_file_id(
                layout, stored_file.id
            )
        except Exception:
            await self.storage_service.delete_object(stored_object.key)
            raise
        if old_stored_file is not None:
            await self.storage_service.delete_object(old_stored_file.storage_key)
            await self.kp_repository.delete_stored_file(old_stored_file)
        return await self._build_single_layout(updated)

    async def delete_background(self, layout_id: UUID) -> VenueLayoutResult:
        require_kp_president_user(self.current_user)
        layout = await self._get_layout(layout_id)
        stored_file = layout.background_stored_file
        if stored_file is None:
            return await self._build_single_layout(layout)
        updated = await self.venue_repository.set_layout_background_stored_file_id(
            layout, None
        )
        await self.storage_service.delete_object(stored_file.storage_key)
        await self.kp_repository.delete_stored_file(stored_file)
        return await self._build_single_layout(updated)

    async def replace_zone_shapes(
        self, layout_id: UUID, shapes: Sequence[VenueZoneShapeInput]
    ) -> VenueLayoutResult:
        require_kp_president_user(self.current_user)
        layout = await self._get_layout(layout_id)
        for shape_input in shapes:
            await self._get_event_zone(
                layout.event_id, shape_input.booth_zone_id, "venue_shapes"
            )
            self._ensure_within_bounds(
                layout_bounds(layout),
                shape_extent_points(shape_input.shape),
                "venue_shapes",
            )
            if shape_input.label_position is not None:
                self._ensure_within_bounds(
                    layout_bounds(layout),
                    [shape_input.label_position],
                    "venue_shape_label",
                )
        await self.venue_repository.replace_zone_shapes(layout, shapes)
        return await self._build_single_layout(layout)

    async def replace_booths(
        self, layout_id: UUID, booths: Sequence[VenueBoothInput]
    ) -> VenueLayoutResult:
        require_kp_president_user(self.current_user)
        layout = await self._get_layout(layout_id)
        seen_booth_numbers: set[int] = set()
        for booth_input in booths:
            if booth_input.booth_nr in seen_booth_numbers:
                raise KpVenueBoothNumberDuplicate(
                    f"venue_booths:duplicate:{layout_id}:{booth_input.booth_nr}"
                )
            seen_booth_numbers.add(booth_input.booth_nr)
            await self._get_event_zone(
                layout.event_id, booth_input.booth_zone_id, "venue_booths"
            )
            self._ensure_within_bounds(
                layout_bounds(layout), [(booth_input.x, booth_input.y)], "venue_booths"
            )
        await self.venue_repository.replace_booths(layout, booths)
        return await self._build_single_layout(layout)

    async def _own_booking(self, event_id: UUID) -> VenueOwnBookingResult | None:
        company_id = self.current_user.company_id
        if company_id is None:
            return None
        booking = await self.kp_repository.get_company_active_booking_for_event(
            event_id, company_id
        )
        if booking is None:
            return None
        return VenueOwnBookingResult(
            booking_id=booking.id,
            booth_zone_id=booking.booth_zone_id,
            booth_nr=booking.booth_nr,
        )

    def _map_layout(
        self, layout: VenueLayoutResult, own_booking: VenueOwnBookingResult | None
    ) -> VenueMapLayoutResult:
        return VenueMapLayoutResult(
            **layout.model_dump(exclude={"booths"}),
            booths=[
                VenueMapBoothResponse(
                    **booth.model_dump(),
                    is_own_booking=own_booking is not None
                    and own_booking.booth_nr == booth.booth_nr
                    and own_booking.booth_zone_id == booth.booth_zone_id,
                )
                for booth in layout.booths
            ],
        )

    async def get_event_venue(self, event_id: UUID) -> VenueMapResult:
        await self._get_event(event_id)
        layouts = await self._build_layouts(
            await self.venue_repository.list_active_layouts(event_id)
        )
        own_booking = await self._own_booking(event_id)
        return VenueMapResult(
            event_id=event_id,
            layouts=[self._map_layout(layout, own_booking) for layout in layouts],
            zones=await booth_zones_with_availability(
                self.kp_repository, self.download_urls, event_id
            ),
            own_booking=own_booking,
        )
