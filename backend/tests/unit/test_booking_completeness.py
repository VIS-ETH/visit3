from collections.abc import Callable
from uuid import uuid4

import pytest

from app.models.company import Company, KpCompanyProfile
from app.models.kp_event import (
    KpEventBooking,
    KpEventBookingService,
    KpEventBookingServiceFileLink,
    KpEventService,
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.services.booking_completeness import (
    BILLING_ADDRESS_MISSING,
    COMPANY_DESCRIPTION_MISSING,
    COMPANY_PROFILE_MISSING,
    GENERAL_EMAIL_MISSING,
    booking_completeness,
    has_billing_address,
    missing_billing_fields,
    requirement_missing_item,
)
from tests.unit.conftest import complete_company_profile, complete_company_snapshot

REQUIREMENT_DESCRIPTION = "Please upload the booth logo as a PNG file."


def make_requirement(
    requirement_type: KpEventServiceRequirementType = KpEventServiceRequirementType.TEXT,
) -> KpEventServiceRequirement:
    return KpEventServiceRequirement(
        id=uuid4(),
        service_id=uuid4(),
        type=requirement_type,
        name="Booth logo",
        description=REQUIREMENT_DESCRIPTION,
    )


def make_booking_service(
    requirements: list[KpEventServiceRequirement],
    answers: list[KpEventBookingServiceFileLink],
) -> KpEventBookingService:
    service = KpEventService(id=uuid4(), event_id=uuid4(), name="Power", description="")
    service.requirements = requirements
    booking_service = KpEventBookingService(
        id=uuid4(), booking_id=uuid4(), service_id=service.id
    )
    booking_service.service = service
    booking_service.requirement_file_links = answers
    return booking_service


def make_booking(
    *,
    booking_services: list[KpEventBookingService] | None = None,
    company_details: bool = True,
    snapshot_overrides: dict[str, object] | None = None,
) -> KpEventBooking:
    booking = KpEventBooking(
        id=uuid4(), event_id=uuid4(), company_id=uuid4(), booth_zone_id=uuid4()
    )
    booking.services = booking_services or []
    booking.company_details = (
        complete_company_snapshot(booking.id, **(snapshot_overrides or {}))
        if company_details
        else None
    )
    company = Company(id=booking.company_id, name="Acme AG")
    company.kp_profile = complete_company_profile(company.id)
    booking.company = company
    return booking


def test_complete_booking_has_no_missing_items():
    requirement = make_requirement()
    answer = KpEventBookingServiceFileLink(
        booking_service_id=uuid4(), requirement_id=requirement.id, text_value="Answer"
    )
    booking = make_booking(
        booking_services=[make_booking_service([requirement], [answer])]
    )

    assert booking_completeness(booking) == []


def test_unanswered_requirement_is_reported_per_requirement():
    first = make_requirement()
    second = make_requirement(KpEventServiceRequirementType.PDF)
    answer = KpEventBookingServiceFileLink(
        booking_service_id=uuid4(), requirement_id=first.id, stored_file_id=uuid4()
    )
    booking = make_booking(
        booking_services=[make_booking_service([first, second], [answer])]
    )

    assert booking_completeness(booking) == [requirement_missing_item(second.id)]


def test_blank_text_answer_does_not_complete_a_requirement():
    requirement = make_requirement()
    answer = KpEventBookingServiceFileLink(
        booking_service_id=uuid4(), requirement_id=requirement.id, text_value=""
    )
    booking = make_booking(
        booking_services=[make_booking_service([requirement], [answer])]
    )

    assert booking_completeness(booking) == [requirement_missing_item(requirement.id)]


def test_missing_company_details_snapshot_is_reported():
    booking = make_booking(company_details=False)

    assert booking_completeness(booking) == [
        COMPANY_PROFILE_MISSING,
        BILLING_ADDRESS_MISSING,
    ]


@pytest.mark.parametrize(
    "missing_field",
    [
        "billing_company_name",
        "billing_street",
        "billing_postal_code",
        "billing_city",
        "billing_country",
        "billing_email",
    ],
)
def test_missing_billing_address_is_reported(missing_field: str):
    booking = make_booking(snapshot_overrides={missing_field: ""})

    assert booking_completeness(booking) == [BILLING_ADDRESS_MISSING]


def test_a_later_profile_edit_does_not_change_the_booking(
    make_company_profile: Callable[..., KpCompanyProfile],
):
    booking = make_booking()
    booking.company.kp_profile = make_company_profile(billing_city="")

    assert booking_completeness(booking) == []


def test_a_missing_description_is_reported():
    booking = make_booking(snapshot_overrides={"description": " "})

    assert booking_completeness(booking) == [COMPANY_DESCRIPTION_MISSING]


def test_a_missing_general_email_is_reported():
    booking = make_booking(snapshot_overrides={"general_email": None})

    assert booking_completeness(booking) == [GENERAL_EMAIL_MISSING]


def test_an_optional_billing_field_does_not_block_the_booking():
    booking = make_booking(
        snapshot_overrides={"billing_house_number": "", "billing_vat_number": None}
    )

    assert booking_completeness(booking) == []


def test_every_missing_item_is_collected():
    requirement = make_requirement()
    booking = make_booking(
        booking_services=[make_booking_service([requirement], [])],
        company_details=False,
    )

    assert booking_completeness(booking) == [
        requirement_missing_item(requirement.id),
        COMPANY_PROFILE_MISSING,
        BILLING_ADDRESS_MISSING,
    ]


def test_billing_address_check_accepts_a_complete_snapshot():
    assert has_billing_address(complete_company_snapshot(uuid4())) is True


def test_billing_address_check_rejects_a_blank_billing_city():
    snapshot = complete_company_snapshot(uuid4(), billing_city="   ")

    assert has_billing_address(snapshot) is False


def test_billing_address_check_rejects_a_missing_snapshot():
    assert has_billing_address(None) is False


def test_missing_billing_fields_names_only_billing_fields():
    snapshot = complete_company_snapshot(
        uuid4(), description="", billing_street="", billing_email=None
    )

    assert missing_billing_fields(snapshot) == ["billing_street", "billing_email"]


def test_missing_billing_fields_of_a_missing_snapshot_are_all_mandatory_ones():
    assert missing_billing_fields(None) == [
        "billing_company_name",
        "billing_street",
        "billing_postal_code",
        "billing_city",
        "billing_country",
        "billing_email",
    ]
