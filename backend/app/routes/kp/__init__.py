from fastapi import APIRouter

from app.core.deps import CsrfDep
from app.routes.kp import (
    bookings,
    booth_zones,
    events,
    exports,
    media,
    requirements,
    services,
)

router = APIRouter(prefix="/kp", tags=["kp"], dependencies=[CsrfDep])

for module in (events, booth_zones, services, bookings, requirements, exports, media):
    router.include_router(module.router)
