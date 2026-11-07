from app.repositories.kp_repository.booking_services import BookingServicesMixin
from app.repositories.kp_repository.bookings import BookingsMixin
from app.repositories.kp_repository.events import EventsMixin
from app.repositories.kp_repository.files import FilesMixin
from app.repositories.kp_repository.nametags import NametagsMixin
from app.repositories.kp_repository.requirements import RequirementsMixin
from app.repositories.kp_repository.services import ServicesMixin
from app.repositories.kp_repository.waitlist import WaitlistMixin
from app.repositories.kp_repository.zones import ZonesMixin


class KpRepository(
    EventsMixin,
    ZonesMixin,
    ServicesMixin,
    BookingsMixin,
    BookingServicesMixin,
    WaitlistMixin,
    NametagsMixin,
    RequirementsMixin,
    FilesMixin,
):
    pass
