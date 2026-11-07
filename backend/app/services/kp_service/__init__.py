from app.services.kp_service.booking_status import BookingStatusMixin
from app.services.kp_service.bookings import BookingsMixin
from app.services.kp_service.events import EventsMixin
from app.services.kp_service.nametags import NametagsMixin
from app.services.kp_service.offers import OffersMixin
from app.services.kp_service.requirements import RequirementsMixin
from app.services.kp_service.services import ServicesMixin
from app.services.kp_service.staff_bookings import StaffBookingsMixin
from app.services.kp_service.waitlist import WaitlistMixin
from app.services.kp_service.zones import ZonesMixin


class KpService(
    EventsMixin,
    ZonesMixin,
    ServicesMixin,
    BookingsMixin,
    StaffBookingsMixin,
    OffersMixin,
    BookingStatusMixin,
    WaitlistMixin,
    NametagsMixin,
    RequirementsMixin,
):
    pass
