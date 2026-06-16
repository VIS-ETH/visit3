"""Shared factory functions for unit tests.

These helpers construct model instances with sensible defaults so tests don't
repeat the same boilerplate.  All keyword arguments are optional — override
only the fields you care about.
"""

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

from pypdf import PdfWriter

from app.models.company import Company, CompanyInvite
from app.models.kp_event import (
    KpBookingStatus,
    KpEvent,
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventBoothZone,
    KpEventService,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.models.storage import StoredFile

# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------


def build_pdf(page_count: int = 1) -> bytes:
    """Return a minimal valid PDF with the given number of pages."""
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Stored file
# ---------------------------------------------------------------------------


def make_stored_file(
    *,
    storage_key: str = "old/key.pdf",
    original_filename: str = "old.pdf",
    mime_type: str = "application/pdf",
    size_bytes: int = 7,
) -> StoredFile:
    return StoredFile(
        id=uuid4(),
        storage_key=storage_key,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256="a" * 64,
        etag="old-etag",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# KP event / zone / booking factories
# ---------------------------------------------------------------------------


def make_event(*, event_id=None, name: str = "Kontaktparty") -> KpEvent:
    today = date.today()
    return KpEvent(
        id=event_id or uuid4(),
        name=name,
        registration_open=today - timedelta(days=1),
        registration_end=today + timedelta(days=1),
        finalization_deadline=today + timedelta(days=2),
        nametags_deadline=today + timedelta(days=3),
        event_date=today + timedelta(days=10),
    )


def make_closed_event(*, event_id=None, name: str = "Kontaktparty") -> KpEvent:
    today = date.today()
    return KpEvent(
        id=event_id or uuid4(),
        name=name,
        registration_open=today - timedelta(days=10),
        registration_end=today - timedelta(days=5),
        finalization_deadline=today - timedelta(days=4),
        nametags_deadline=today - timedelta(days=3),
        event_date=today + timedelta(days=10),
    )


def make_zone(
    *, event_id, zone_id=None, capacity: int = 2
) -> KpEventBoothZone:
    return KpEventBoothZone(
        id=zone_id or uuid4(),
        event_id=event_id,
        name="Main Hall",
        description="Main booth zone",
        capacity=capacity,
    )


def make_booking(
    *,
    event_id=None,
    company_id=None,
    booth_zone_id=None,
    status: KpBookingStatus = KpBookingStatus.REGISTERED,
) -> KpEventBooking:
    return KpEventBooking(
        id=uuid4(),
        event_id=event_id or uuid4(),
        company_id=company_id or uuid4(),
        booth_zone_id=booth_zone_id or uuid4(),
        status=status,
    )


def attach_staff_booking_relations(booking: KpEventBooking) -> KpEventBooking:
    """Attach company, zone, services, name_tags etc. to a booking for tests."""
    booking.company = Company(id=booking.company_id, name="Acme AG")
    booking.booth_zone = make_zone(
        event_id=booking.event_id,
        zone_id=booking.booth_zone_id,
    )
    booking.services = []
    booking.name_tags = []
    booking.upgrade_waitlist_entries = []
    booking.company_details = None
    return booking


def make_service(
    *,
    event_id,
    service_id=None,
    is_active: bool = True,
    max_quantity_per_booking: int = 3,
    max_total_quantity: int = 0,
) -> KpEventService:
    return KpEventService(
        id=service_id or uuid4(),
        event_id=event_id,
        name="Power",
        description="Power connection",
        price=10000,
        is_active=is_active,
        max_quantity_per_booking=max_quantity_per_booking,
        max_total_quantity=max_total_quantity,
    )


def make_requirement(
    *,
    service_id,
    requirement_type: KpEventServiceRequirementType = KpEventServiceRequirementType.PDF,
) -> KpEventServiceRequirement:
    return KpEventServiceRequirement(
        id=uuid4(),
        service_id=service_id,
        type=requirement_type,
        name="Upload file",
        description="Please upload the requested file.",
    )


def make_booking_service(
    *,
    booking: KpEventBooking,
    service_id=None,
) -> KpEventBookingService:
    return KpEventBookingService(
        id=uuid4(),
        booking_id=booking.id,
        service_id=service_id or uuid4(),
        booking=booking,
    )


def make_requirement_file(
    *,
    booking_service: KpEventBookingService,
    requirement: KpEventServiceRequirement,
    stored_file: StoredFile | None = None,
) -> KpEventBookingServiceFileLink:
    stored_file = stored_file or make_stored_file()
    return KpEventBookingServiceFileLink(
        id=uuid4(),
        booking_service_id=booking_service.id,
        requirement_id=requirement.id,
        stored_file_id=stored_file.id,
        booking_service=booking_service,
        requirement=requirement,
        stored_file=stored_file,
    )


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------


def make_invite(
    *,
    token: str = "invite-token",
    company_id=None,
    invited_email: str = "user@example.com",
    is_used: bool = False,
    expires_at: datetime | None = None,
) -> CompanyInvite:
    return CompanyInvite(
        token=token,
        company_id=company_id or uuid4(),
        invited_email=invited_email,
        is_used=is_used,
        expires_at=expires_at or datetime.now(timezone.utc) + timedelta(days=1),
    )
