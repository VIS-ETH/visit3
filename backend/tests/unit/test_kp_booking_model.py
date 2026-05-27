from uuid import uuid4

from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingUpgradeWaitlist,
    KpEventBoothZone,
    KpEventService,
    NameTag,
)


def test_booking_summary_properties_include_related_booking_information():
    event_id = uuid4()
    booking = KpEventBooking(
        event_id=event_id,
        company_id=uuid4(),
        booth_zone_id=uuid4(),
    )
    booking.booth_zone = KpEventBoothZone(
        event_id=event_id,
        name="Standard",
        description="",
        base_price=10000,
    )
    booking.services = [
        KpEventBookingService(
            service=KpEventService(
                event_id=event_id,
                name="Power",
                description="",
                price=2500,
            ),
            quantity=3,
            included_quantity=1,
        )
    ]
    booking.name_tags = [
        NameTag(first_name="Ada", last_name="Lovelace", position="Engineer"),
        NameTag(first_name="Grace", last_name="Hopper", position="Scientist"),
    ]
    booking.upgrade_waitlist_entries = [
        KpEventBookingUpgradeWaitlist(target_booth_zone_id=uuid4())
    ]

    assert booking.total_price == 15000
    assert booking.booked_services_count == 1
    assert booking.booked_services_summary == "Power x3"
    assert booking.nametag_count == 2
    assert booking.waitlist_count == 1
    assert not booking.company_details_submitted

    booking.company_details = KpBookingCompanyDetails()

    assert booking.company_details_submitted
