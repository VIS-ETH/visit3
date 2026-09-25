from uuid import UUID

from app.models.kp_event import KpEventBoothZone
from app.repositories.kp_repository import KpRepository
from app.schemas.kp import (
    BoothZoneResponse,
    BoothZoneWithAvailabilityResult,
    StaffBoothZoneResponse,
)
from app.services.download_urls import DownloadUrls


async def staff_booth_zone_response(
    zone: KpEventBoothZone, download_urls: DownloadUrls
) -> StaffBoothZoneResponse:
    response = StaffBoothZoneResponse.model_validate(zone, from_attributes=True)
    return response.model_copy(
        update={"layout_url": await download_urls.of(zone.layout_stored_file)}
    )


async def booth_zone_response(
    zone: KpEventBoothZone, download_urls: DownloadUrls
) -> BoothZoneResponse:
    staff_response = await staff_booth_zone_response(zone, download_urls)
    return BoothZoneResponse.model_validate(
        staff_response.model_dump(exclude={"capacity"})
    )


async def booth_zones_with_availability(
    kp_repository: KpRepository, download_urls: DownloadUrls, event_id: UUID
) -> list[BoothZoneWithAvailabilityResult]:
    availability: list[BoothZoneWithAvailabilityResult] = []
    for zone in await kp_repository.list_booth_zones(event_id):
        taken = await kp_repository.count_active_bookings_for_zone(event_id, zone.id)
        zone_response = await booth_zone_response(zone, download_urls)
        availability.append(
            BoothZoneWithAvailabilityResult(
                **zone_response.model_dump(),
                is_full=taken >= zone.capacity,
            )
        )
    return availability
