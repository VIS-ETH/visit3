from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.company import KpCompanyProfile
from app.models.kp_event import KpBookingStatus, KpEventBooking
from app.models.user import User

KP_PRESIDENT_ROLE = get_settings().VISIT_KP_PRESIDENT_ROLE
ACME_CONTACT = "company@example.com"
NEWCOMER_GENERAL = "hello@newcomer.example"

CAMPAIGN_TEXTS = {
    "subject_de": "Anmeldung für {{ event_name }}",
    "subject_en": "Registration for {{ event_name }}",
    "body_de": '<p>Hallo {{ name }}, <a href="{{ login_url }}">anmelden</a>.</p>',
    "body_en": '<p>Hello {{ name }}, <a href="{{ login_url }}">register</a>.</p>',
}


@dataclass(frozen=True)
class CampaignWorld:
    event_id: str
    booth_zone_id: str
    acme_id: UUID
    newcomer_id: UUID
    silent_id: UUID


def sent_messages(mail_stub: AsyncMock) -> list[Any]:
    return [call.args[0] for call in mail_stub.SendMail.await_args_list]


def recipients_of(message: Any) -> list[str]:
    return [address.mail_address.address for address in message.to]


def sent_addresses(mail_stub: AsyncMock) -> list[str]:
    return sorted(
        address
        for message in sent_messages(mail_stub)
        for address in recipients_of(message)
    )


def campaign_payload(world: CampaignWorld, **overrides: Any) -> dict[str, Any]:
    return {
        "name": "Registration reminder",
        "event_id": world.event_id,
        **CAMPAIGN_TEXTS,
        "audience": {"segments": ["NOT_REGISTERED", "REGISTERED"]},
        **overrides,
    }


async def add_profile(
    db_session: AsyncSession,
    company_id: UUID,
    *,
    contact: User | None = None,
    general_email: str | None = None,
) -> None:
    db_session.add(
        KpCompanyProfile(
            company_id=company_id,
            general_email=general_email,
            kp_contact_user_id=contact.id if contact is not None else None,
            languages=[],
        )
    )
    await db_session.commit()


async def add_booking(
    db_session: AsyncSession,
    world: CampaignWorld,
    company_id: UUID,
    status: KpBookingStatus = KpBookingStatus.REGISTERED,
) -> None:
    db_session.add(
        KpEventBooking(
            event_id=UUID(world.event_id),
            company_id=company_id,
            booth_zone_id=UUID(world.booth_zone_id),
            status=status,
        )
    )
    await db_session.commit()


async def create_campaign(
    client: AsyncClient,
    headers: dict[str, str],
    world: CampaignWorld,
    **overrides: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/api/mail-campaigns",
        json=campaign_payload(world, **overrides),
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()
