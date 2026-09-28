from uuid import UUID

from app.models.company import MANDATORY_PROFILE_FIELDS
from app.models.kp_event import (
    KpBookingCompanyDetails,
    KpEventBooking,
    KpEventBookingService,
    KpEventServiceRequirement,
)

MissingItem = str

COMPANY_PROFILE_MISSING = "company_profile"
COMPANY_DESCRIPTION_MISSING = "company_description"
BILLING_ADDRESS_MISSING = "billing_address"
GENERAL_EMAIL_MISSING = "general_email"
BILLING_FIELD_PREFIX = "billing_"
MANDATORY_BILLING_FIELDS = tuple(
    name for name in MANDATORY_PROFILE_FIELDS if name.startswith(BILLING_FIELD_PREFIX)
)


def requirement_missing_item(requirement_id: UUID) -> MissingItem:
    return f"requirement:{requirement_id}"


def missing_billing_fields(snapshot: KpBookingCompanyDetails | None) -> list[str]:
    if snapshot is None:
        return list(MANDATORY_BILLING_FIELDS)
    return [
        name
        for name in MANDATORY_BILLING_FIELDS
        if not str(getattr(snapshot, name) or "").strip()
    ]


def has_billing_address(snapshot: KpBookingCompanyDetails | None) -> bool:
    return not missing_billing_fields(snapshot)


def _is_answered(
    booking_service: KpEventBookingService, requirement: KpEventServiceRequirement
) -> bool:
    return any(
        answer.requirement_id == requirement.id
        and (answer.stored_file_id is not None or bool(answer.text_value))
        for answer in booking_service.requirement_file_links
    )


def booking_completeness(booking: KpEventBooking) -> list[MissingItem]:
    missing = [
        requirement_missing_item(requirement.id)
        for booking_service in booking.services
        for requirement in booking_service.service.requirements
        if not _is_answered(booking_service, requirement)
    ]
    if booking.company_details is None:
        missing.append(COMPANY_PROFILE_MISSING)
    else:
        if not booking.company_details.description.strip():
            missing.append(COMPANY_DESCRIPTION_MISSING)
        if not str(booking.company_details.general_email or "").strip():
            missing.append(GENERAL_EMAIL_MISSING)
    if not has_billing_address(booking.company_details):
        missing.append(BILLING_ADDRESS_MISSING)
    return missing
