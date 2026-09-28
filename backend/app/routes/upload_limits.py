from collections.abc import Callable

from app.core.config import get_settings
from app.routes.company import (
    upload_company_profile_logo,
    upload_my_company_profile_logo,
)
from app.routes.kp import (
    upload_booking_requirement_file,
    upload_booklet_background,
    upload_booth_zone_layout_file,
    upload_event_banner,
    upload_nametag_export_background,
    upload_service_image,
)
from app.routes.venue import upload_venue_layout_background
from app.services.event_banner_service import BANNER_MAX_BYTES
from app.services.storage_service import UploadKind, upload_limit_bytes


def upload_route_limits() -> dict[Callable[..., object], int]:
    settings = get_settings()
    image = upload_limit_bytes(settings, UploadKind.IMAGE)
    pdf = upload_limit_bytes(settings, UploadKind.PDF)
    largest = max(upload_limit_bytes(settings, kind) for kind in UploadKind)
    return {
        upload_my_company_profile_logo: image,
        upload_company_profile_logo: image,
        upload_service_image: image,
        upload_nametag_export_background: image,
        upload_venue_layout_background: image,
        upload_booth_zone_layout_file: pdf,
        upload_booklet_background: pdf,
        upload_event_banner: BANNER_MAX_BYTES,
        upload_booking_requirement_file: largest,
    }
