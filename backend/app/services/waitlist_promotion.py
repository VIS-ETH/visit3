from uuid import UUID

from app.models.kp_event import KpBookingStatus, KpEvent
from app.repositories.kp_repository import KpRepository
from app.services.booking_notifier import BookingNotifier, notify_best_effort
from app.services.zone_switch_stock import service_exceeding_stock


async def promote_waitlist(
    kp_repository: KpRepository,
    notifier: BookingNotifier,
    event_id: UUID,
    booth_zone_id: UUID,
) -> None:
    event = await kp_repository.lock_model_by_id(KpEvent, event_id)
    zone = await kp_repository.get_booth_zone_by_id(booth_zone_id)
    if event is None or zone is None or zone.event_id != event_id:
        return
    if event.is_finalization_deadline_passed():
        return

    for entry in await kp_repository.list_waitlist_entries_for_zone(booth_zone_id):
        taken = await kp_repository.count_active_bookings_for_zone(
            event_id, booth_zone_id
        )
        if taken >= zone.capacity:
            return
        booking = await kp_repository.get_booking_by_id(entry.booking_id)
        if booking is None or not booking.is_active:
            await kp_repository.delete_waitlist_entry(entry)
            continue
        if booking.status != KpBookingStatus.REGISTERED:
            continue
        if await service_exceeding_stock(kp_repository, booking, zone) is not None:
            continue
        promoted = await kp_repository.move_booking_to_zone(
            booking, zone, clear_whole_waitlist=True
        )
        await notify_best_effort(notifier.waitlist_promoted(promoted))
