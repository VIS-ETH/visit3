from datetime import date
from uuid import uuid4

from app.models.mail import (
    MailCampaignRecipientSource,
    MailCampaignSegment,
    MailCampaignSkipReason,
)
from app.schemas.mail_campaign import MailCampaignAudience
from app.services.mail_campaign_audience import (
    AudienceCompany,
    AudienceContact,
    AudienceData,
    AudienceEvent,
    plan_recipients,
)

DAY = date(2030, 1, 1)
EVENT = AudienceEvent(uuid4(), "Kontaktparty", DAY, DAY, DAY, DAY)


def test_a_shared_address_goes_to_the_company_where_it_belongs_to_a_person():
    boss = AudienceContact(user_id=uuid4(), email="boss@beta.example", name="Boss")
    agency = AudienceCompany(
        id=uuid4(), name="Alpha AG", contact=None, general_email="Boss@Beta.example"
    )
    beta = AudienceCompany(id=uuid4(), name="Beta AG", contact=boss, general_email=None)
    data = AudienceData(event=EVENT, companies=[agency, beta], bookings=[])

    planned = plan_recipients(
        MailCampaignAudience(segments=[MailCampaignSegment.ALL]), data
    )

    assert [
        (entry.company.name, entry.source, entry.skip_reason, entry.person)
        for entry in planned
    ] == [
        (
            "Alpha AG",
            MailCampaignRecipientSource.GENERAL_EMAIL,
            MailCampaignSkipReason.DUPLICATE_ADDRESS,
            None,
        ),
        ("Beta AG", MailCampaignRecipientSource.CONTACT, None, boss),
    ]
