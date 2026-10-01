from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.models.kp_event import KpBookingStatus
from app.models.mail import (
    MailCampaignRecipientSource,
    MailCampaignSegment,
    MailCampaignSkipReason,
)
from app.models.user import User
from app.schemas.mail_campaign import MailCampaignAudience
from app.services.mail_campaign_audience import (
    AudienceBooking,
    AudienceCompany,
    AudienceContact,
    AudienceData,
    AudienceEvent,
    campaign_context,
    eligible_contact,
    plan_recipients,
)

EVENT = AudienceEvent(
    id=uuid4(),
    name="Kontaktparty 2026",
    event_date=date(2026, 10, 20),
    registration_end=date(2026, 9, 15),
    finalization_deadline=date(2026, 9, 30),
    nametags_deadline=date(2026, 10, 5),
)
MAIN_HALL = uuid4()
SIDE_HALL = uuid4()
ZONE_NAMES = {MAIN_HALL: "Main hall", SIDE_HALL: "Side hall"}


def company(name: str, *, contact: bool = True, general: bool = True):
    slug = name.lower().replace(" ", "")
    return AudienceCompany(
        id=uuid4(),
        name=name,
        contact=AudienceContact(
            user_id=uuid4(), email=f"contact@{slug}.example", name=f"{name} Contact"
        )
        if contact
        else None,
        general_email=f"info@{slug}.example" if general else None,
    )


def booking(
    owner: AudienceCompany,
    status: KpBookingStatus,
    zone: UUID = MAIN_HALL,
    *,
    waitlisted: bool = False,
    offer_deadline: date | None = None,
) -> AudienceBooking:
    return AudienceBooking(
        id=uuid4(),
        company_id=owner.id,
        status=status,
        booth_zone_id=zone,
        booth_zone_name=ZONE_NAMES[zone],
        offer_deadline=offer_deadline,
        waitlisted=waitlisted,
    )


NEWCOMER = company("Newcomer")
REGISTERED = company("Registered")
CONFIRMED = company("Confirmed")
OFFERED = company("Offered")
WAITLISTED = company("Waitlisted")
SIDE = company("Side")
CANCELLED = company("Cancelled")

DATA = AudienceData(
    event=EVENT,
    companies=[NEWCOMER, REGISTERED, CONFIRMED, OFFERED, WAITLISTED, SIDE, CANCELLED],
    bookings=[
        booking(REGISTERED, KpBookingStatus.REGISTERED),
        booking(CONFIRMED, KpBookingStatus.CONFIRMED),
        booking(OFFERED, KpBookingStatus.OFFERED, offer_deadline=date(2026, 9, 20)),
        booking(WAITLISTED, KpBookingStatus.REGISTERED, SIDE_HALL, waitlisted=True),
        booking(SIDE, KpBookingStatus.CONFIRMED, SIDE_HALL),
        booking(CANCELLED, KpBookingStatus.CANCELLED),
    ],
)


def names(audience: MailCampaignAudience, data: AudienceData = DATA) -> list[str]:
    return [planned.company.name for planned in plan_recipients(audience, data)]


def segments(*values: MailCampaignSegment) -> MailCampaignAudience:
    return MailCampaignAudience(segments=list(values))


@pytest.mark.parametrize(
    ("segment", "expected"),
    [
        (
            MailCampaignSegment.ALL,
            [
                "Cancelled",
                "Confirmed",
                "Newcomer",
                "Offered",
                "Registered",
                "Side",
                "Waitlisted",
            ],
        ),
        (MailCampaignSegment.NOT_REGISTERED, ["Cancelled", "Newcomer"]),
        (
            MailCampaignSegment.REGISTERED,
            ["Confirmed", "Registered", "Side", "Waitlisted"],
        ),
        (MailCampaignSegment.CONFIRMED, ["Confirmed", "Side"]),
        (MailCampaignSegment.OFFERED, ["Offered"]),
        (MailCampaignSegment.WAITLISTED, ["Waitlisted"]),
    ],
)
def test_each_segment_selects_its_companies(
    segment: MailCampaignSegment, expected: list[str]
):
    assert names(segments(segment)) == expected


def test_segments_combine_as_a_union():
    assert names(
        segments(MailCampaignSegment.NOT_REGISTERED, MailCampaignSegment.OFFERED)
    ) == ["Cancelled", "Newcomer", "Offered"]


def test_zones_narrow_the_booking_segments():
    audience = MailCampaignAudience(
        segments=[MailCampaignSegment.REGISTERED], booth_zone_ids=[SIDE_HALL]
    )

    assert names(audience) == ["Side", "Waitlisted"]


def test_all_companies_in_a_zone_means_every_active_booking_there():
    audience = MailCampaignAudience(
        segments=[MailCampaignSegment.ALL], booth_zone_ids=[MAIN_HALL]
    )

    assert names(audience) == ["Confirmed", "Offered", "Registered"]


def test_zones_do_not_hide_companies_without_a_booking():
    audience = MailCampaignAudience(
        segments=[MailCampaignSegment.NOT_REGISTERED, MailCampaignSegment.CONFIRMED],
        booth_zone_ids=[SIDE_HALL],
    )

    assert names(audience) == ["Cancelled", "Newcomer", "Side"]


def test_an_empty_audience_reaches_nobody():
    assert names(MailCampaignAudience()) == []


def test_manual_includes_add_companies_outside_the_filters():
    audience = MailCampaignAudience(
        segments=[MailCampaignSegment.OFFERED], include_company_ids=[CONFIRMED.id]
    )

    planned = plan_recipients(audience, DATA)

    assert [(entry.company.name, entry.manually_included) for entry in planned] == [
        ("Confirmed", True),
        ("Offered", False),
    ]


def test_manual_excludes_win_over_the_filters():
    audience = MailCampaignAudience(
        segments=[MailCampaignSegment.CONFIRMED], exclude_company_ids=[SIDE.id]
    )

    assert names(audience) == ["Confirmed"]


def test_a_company_cannot_be_included_and_excluded():
    with pytest.raises(ValueError):
        MailCampaignAudience(
            include_company_ids=[SIDE.id], exclude_company_ids=[SIDE.id]
        )


def test_the_primary_contact_is_preferred_over_the_general_email():
    [planned] = plan_recipients(
        MailCampaignAudience(include_company_ids=[NEWCOMER.id]), DATA
    )

    assert planned.email == "contact@newcomer.example"
    assert planned.source == MailCampaignRecipientSource.CONTACT
    assert planned.skip_reason is None


def test_the_general_email_is_the_fallback_without_a_contact():
    lonely = company("Lonely", contact=False)
    data = AudienceData(event=EVENT, companies=[lonely], bookings=[])

    [planned] = plan_recipients(segments(MailCampaignSegment.ALL), data)

    assert planned.email == "info@lonely.example"
    assert planned.source == MailCampaignRecipientSource.GENERAL_EMAIL


def test_companies_without_any_address_are_skipped_visibly():
    silent = company("Silent", contact=False, general=False)
    data = AudienceData(event=EVENT, companies=[silent], bookings=[])

    [planned] = plan_recipients(segments(MailCampaignSegment.ALL), data)

    assert planned.email is None
    assert planned.skip_reason == MailCampaignSkipReason.NO_ADDRESS


def test_addresses_are_deduplicated_case_insensitively():
    shared = AudienceContact(user_id=uuid4(), email="Agency@Example.com", name="Ag")
    first = AudienceCompany(
        id=uuid4(), name="Alpha", contact=shared, general_email=None
    )
    second = AudienceCompany(
        id=uuid4(), name="Beta", contact=None, general_email="agency@example.com "
    )
    data = AudienceData(event=EVENT, companies=[second, first], bookings=[])

    planned = plan_recipients(segments(MailCampaignSegment.ALL), data)

    assert [(entry.company.name, entry.skip_reason) for entry in planned] == [
        ("Alpha", None),
        ("Beta", MailCampaignSkipReason.DUPLICATE_ADDRESS),
    ]


def contact_user(company_id: UUID | None, **overrides: object) -> User:
    values: dict[str, object] = {
        "email": "ada@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email_confirmed": True,
        "company_id": company_id,
        **overrides,
    }
    return User.model_validate(values)


def test_a_confirmed_member_is_an_eligible_contact():
    company_id = uuid4()

    contact = eligible_contact(contact_user(company_id), company_id)

    assert contact is not None
    assert (contact.email, contact.name) == ("ada@example.com", "Ada Lovelace")


@pytest.mark.parametrize(
    "overrides",
    [
        {"email_confirmed": False},
        {"company_id": uuid4()},
        {"deleted_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
    ],
)
def test_unusable_contacts_fall_back(overrides: dict[str, object]):
    company_id = uuid4()
    user = contact_user(company_id)
    for name, value in overrides.items():
        setattr(user, name, value)

    assert eligible_contact(user, company_id) is None
    assert eligible_contact(None, company_id) is None


def test_the_context_carries_the_booking_details():
    context = campaign_context(
        DATA, OFFERED, MailCampaignRecipientSource.CONTACT, "https://visit.test/x"
    )

    assert context.name == "Offered Contact"
    assert context.company_name == "Offered"
    assert context.booth_zone_name == "Main hall"
    assert context.offer_deadline == "2026-09-20"
    assert context.registration_end == "2026-09-15"
    assert context.login_url == "https://visit.test/x"


def test_the_context_greets_the_company_when_the_general_email_is_used():
    context = campaign_context(
        DATA, NEWCOMER, MailCampaignRecipientSource.GENERAL_EMAIL, "u"
    )

    assert context.name == "Newcomer"
    assert context.booth_zone_name == "-"
    assert context.offer_deadline == "-"
