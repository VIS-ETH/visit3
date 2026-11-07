from uuid import UUID

from app.models.kp_event import KpBookingStatus, KpEvent, KpEventBooking
from app.repositories.kp_repository import KpRepository
from app.services.booking_notifier import BookingNotifier, notify_best_effort
from app.services.registration_exceptions import has_registration_exception
from app.services.zone_switch_stock import service_exceeding_stock


async def promote_waitlist(
    kp_repository: KpRepository,
    notifier: BookingNotifier,
    event_id: UUID,
    booth_zone_id: UUID,
) -> None:
    pending = [booth_zone_id]
    while pending:
        zone_id = pending.pop(0)
        while (
            promotion := await _promote_next(kp_repository, event_id, zone_id)
        ) is not None:
            promoted, left_zone_id = promotion
            await notify_best_effort(notifier.waitlist_promoted(promoted))
            pending.append(left_zone_id)


async def _promote_next(
    kp_repository: KpRepository, event_id: UUID, booth_zone_id: UUID
) -> tuple[KpEventBooking, UUID] | None:
    event = await kp_repository.lock_model_by_id(KpEvent, event_id)
    zone = await kp_repository.lock_booth_zone(booth_zone_id)
    if (
        event is None
        or zone is None
        or zone.event_id != event_id
        or event.is_finalization_deadline_passed()
    ):
        await kp_repository.release_locks()
        return None
    for entry in await kp_repository.list_waitlist_entries_for_zone(booth_zone_id):
        taken = await kp_repository.count_active_bookings_for_zone(
            event_id, booth_zone_id
        )
        if taken >= zone.capacity:
            break
        booking = await kp_repository.lock_booking(entry.booking_id)
        if booking is None or not booking.is_active:
            await kp_repository.delete_waitlist_entry(entry)
            return await _promote_next(kp_repository, event_id, booth_zone_id)
        if booking.status != KpBookingStatus.REGISTERED:
            continue
        if not zone.registration_open and not await has_registration_exception(
            kp_repository, event_id, booking.company_id
        ):
            continue
        if await service_exceeding_stock(kp_repository, booking, zone) is not None:
            continue
        left_zone_id = booking.booth_zone_id
        promoted = await kp_repository.move_booking_to_zone(
            booking, zone, clear_whole_waitlist=True
        )
        return promoted, left_zone_id
    await kp_repository.release_locks()
    return None
