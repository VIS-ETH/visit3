import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from app.models.kp_event import KpEvent
from app.models.user import User
from app.services.mail_campaign_delivery import MailCampaignDelivery
from app.services.mail_service import MailService
from tests.api.mail_campaign_helpers import (
    ACME_CONTACT,
    CampaignWorld,
    create_campaign,
    recipients_of,
    sent_messages,
)

BASE = "/api/mail-campaigns"
DUE = datetime(2030, 12, 1, 8, 0, tzinfo=timezone.utc)


async def campaign(
    client: AsyncClient, headers: dict[str, str], campaign_id: str
) -> dict[str, Any]:
    response = await client.get(f"{BASE}/{campaign_id}", headers=headers)
    return response.json()


async def schedule(
    client: AsyncClient, headers: dict[str, str], campaign_id: str
) -> None:
    response = await client.post(
        f"{BASE}/{campaign_id}/schedule",
        json={"scheduled_at": "2030-12-01T09:00"},
        headers=headers,
    )
    assert response.status_code == 200, response.text


async def delete_event(db_session: AsyncSession, event_id: str) -> None:
    statement = select(KpEvent).where(col(KpEvent.id) == UUID(event_id))
    event = (await db_session.execute(statement)).scalar_one()
    event.deleted_at = datetime.now(timezone.utc)
    db_session.add(event)
    await db_session.commit()


async def test_a_retried_mail_to_a_changed_address_carries_no_personal_login_link(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    async def fail_for_acme(message: Any, **_: Any) -> None:
        if recipients_of(message) == [ACME_CONTACT]:
            raise RuntimeError("smtp down")

    mail_stub.SendMail.side_effect = fail_for_acme
    created = await create_campaign(client, president_headers, campaign_world)
    await client.post(f"{BASE}/{created['id']}/send", headers=president_headers)
    statement = select(User).where(col(User.email) == ACME_CONTACT)
    user = (await db_session.execute(statement)).scalar_one()
    user.email = "new-owner@acme.example"
    db_session.add(user)
    await db_session.commit()
    mail_stub.SendMail.side_effect = None
    mail_stub.reset_mock()

    retried = await client.post(
        f"{BASE}/{created['id']}/retry", headers=president_headers
    )

    assert retried.status_code == 200, retried.text
    [message] = sent_messages(mail_stub)
    assert recipients_of(message) == [ACME_CONTACT]
    assert "/auth/link/" not in message.plain_text


async def test_a_template_failing_for_one_company_fails_only_that_recipient(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(
        client,
        president_headers,
        campaign_world,
        subject_en="",
        body_en="",
        body_de='<p>{% if company_name == "Acme AG" or company_name < 1 %}'
        "x{% endif %}</p>",
    )

    sent = await client.post(f"{BASE}/{created['id']}/send", headers=president_headers)

    assert sent.status_code == 200, sent.text
    body = await campaign(client, president_headers, created["id"])
    assert body["status"] == "PARTIALLY_FAILED"
    assert body["counts"]["pending"] == 0
    failed = [entry for entry in body["recipients"] if entry["status"] == "FAILED"]
    assert [entry["error"] for entry in failed] == ["RENDER_FAILED"]
    assert ACME_CONTACT in [recipients_of(m)[0] for m in sent_messages(mail_stub)]


async def test_an_interrupted_recipient_is_not_mailed_again_on_retry(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)
    await schedule(client, president_headers, created["id"])
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)
    release = asyncio.Event()
    hanging_stub = AsyncMock()

    async def hang(message: Any, **_: Any) -> None:
        await release.wait()

    hanging_stub.SendMail.side_effect = hang
    stalled = MailCampaignDelivery(
        sessions, MailService(hanging_stub), pause_seconds=0, clock=lambda: DUE
    )
    takeover = MailCampaignDelivery(
        sessions,
        MailService(AsyncMock()),
        pause_seconds=0,
        clock=lambda: DUE + timedelta(minutes=11),
    )
    stalled_run = asyncio.create_task(stalled.run_due())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if hanging_stub.SendMail.await_count:
            break
    assert await takeover.run_due() == 1
    release.set()
    await stalled_run
    body = await campaign(client, president_headers, created["id"])
    failed = [entry for entry in body["recipients"] if entry["status"] == "FAILED"]
    assert [entry["error"] for entry in failed] == ["INTERRUPTED"]
    mail_stub.reset_mock()

    await client.post(f"{BASE}/{created['id']}/retry", headers=president_headers)

    assert sent_messages(mail_stub) == []
    body = await campaign(client, president_headers, created["id"])
    failed = [entry for entry in body["recipients"] if entry["status"] == "FAILED"]
    assert [entry["error"] for entry in failed] == ["INTERRUPTED"]


async def test_a_campaign_of_a_deleted_event_cannot_be_sent(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)
    await delete_event(db_session, created["event_id"])

    sent = await client.post(f"{BASE}/{created['id']}/send", headers=president_headers)

    assert sent.status_code == 404
    assert (await campaign(client, president_headers, created["id"]))[
        "status"
    ] == "DRAFT"
    assert sent_messages(mail_stub) == []


async def test_a_scheduled_campaign_whose_event_was_deleted_is_not_reported_as_sent(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)
    await schedule(client, president_headers, created["id"])
    await delete_event(db_session, created["event_id"])
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)

    await MailCampaignDelivery(
        sessions, MailService(mail_stub), pause_seconds=0, clock=lambda: DUE
    ).run_due()

    body = await campaign(client, president_headers, created["id"])
    assert body["status"] == "PARTIALLY_FAILED"
    assert sent_messages(mail_stub) == []
