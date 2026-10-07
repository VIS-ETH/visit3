import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from app.core.maintenance import MINUTELY, create_scheduler, dispatch_mail_campaigns
from app.models.mail import (
    MailCampaign,
    MailCampaignRecipient,
    MailCampaignRecipientSource,
    MailCampaignRecipientStatus,
    MailCampaignStatus,
)
from app.repositories.mail_campaign_repository import MailCampaignRepository
from app.services.mail_campaign_delivery import MailCampaignDelivery
from app.services.mail_service import MailService
from tests.api.conftest import shared_session_factory
from tests.api.mail_campaign_helpers import (
    ACME_CONTACT,
    NEWCOMER_GENERAL,
    CampaignWorld,
    add_profile,
    create_campaign,
    recipients_of,
    sent_addresses,
    sent_messages,
)

BASE = "/api/mail-campaigns"
DEC_FIRST_9_ZURICH_IN_UTC = datetime(2030, 12, 1, 8, 0, tzinfo=timezone.utc)
JUL_FIRST_9_ZURICH_IN_UTC = datetime(2030, 7, 1, 7, 0, tzinfo=timezone.utc)
ONE_SECOND = timedelta(seconds=1)


def delivery(
    db_session: AsyncSession, mail_stub: AsyncMock, now: datetime
) -> MailCampaignDelivery:
    return MailCampaignDelivery(
        shared_session_factory(db_session),
        MailService(mail_stub),
        pause_seconds=0,
        clock=lambda: now,
    )


async def scheduled_campaign(
    client: AsyncClient,
    headers: dict[str, str],
    world: CampaignWorld,
    local_time: str = "2030-12-01T09:00",
) -> str:
    created = await create_campaign(client, headers, world)
    response = await client.post(
        f"{BASE}/{created['id']}/schedule",
        json={"scheduled_at": local_time},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return created["id"]


async def campaign(
    client: AsyncClient, headers: dict[str, str], campaign_id: str
) -> dict[str, Any]:
    return (await client.get(f"{BASE}/{campaign_id}", headers=headers)).json()


def recipient_states(body: dict[str, Any]) -> list[tuple[str, str, str | None, int]]:
    return [
        (entry["company_name"], entry["status"], entry["error"], entry["attempts"])
        for entry in body["recipients"]
    ]


def test_the_due_lookup_skips_campaigns_locked_by_another_worker():
    statement = MailCampaignRepository.due_campaign_statement(
        datetime(2030, 1, 1, tzinfo=timezone.utc)
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "FOR UPDATE SKIP LOCKED" in sql


def test_edits_lock_the_campaign_row():
    statement = MailCampaignRepository.locked_campaign_statement(
        UUID("00000000-0000-0000-0000-000000000001")
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "FOR UPDATE OF mailcampaign" in sql


def test_the_scheduler_looks_for_due_campaigns_every_minute():
    scheduler = create_scheduler()

    assert (dispatch_mail_campaigns, MINUTELY) in scheduler._tasks
    assert MINUTELY == 60


@pytest.mark.parametrize(
    ("local_time", "due"),
    [
        ("2030-12-01T09:00", DEC_FIRST_9_ZURICH_IN_UTC),
        ("2030-07-01T09:00", JUL_FIRST_9_ZURICH_IN_UTC),
    ],
)
async def test_a_scheduled_campaign_waits_for_its_zurich_time(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
    local_time: str,
    due: datetime,
):
    campaign_id = await scheduled_campaign(
        client, president_headers, campaign_world, local_time
    )

    early = await delivery(db_session, mail_stub, due - ONE_SECOND).run_due()

    assert early == 0
    assert sent_messages(mail_stub) == []
    assert (await campaign(client, president_headers, campaign_id))[
        "status"
    ] == "SCHEDULED"

    on_time = await delivery(db_session, mail_stub, due).run_due()

    assert on_time == 1
    assert sent_addresses(mail_stub) == [ACME_CONTACT, NEWCOMER_GENERAL]
    body = await campaign(client, president_headers, campaign_id)
    assert body["status"] == "SENT"
    assert body["finished_at"] is not None


async def test_concurrent_ticks_send_every_mail_once(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    campaign_id = await scheduled_campaign(client, president_headers, campaign_world)

    async def slow_send(*_: object) -> None:
        for _ in range(3):
            await asyncio.sleep(0)

    mail_stub.SendMail.side_effect = slow_send
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)
    workers = [
        MailCampaignDelivery(
            sessions,
            MailService(mail_stub),
            pause_seconds=0,
            clock=lambda: DEC_FIRST_9_ZURICH_IN_UTC,
        )
        for _ in range(3)
    ]

    delivered = await asyncio.gather(*(worker.run_due() for worker in workers))

    assert sum(delivered) == 1
    assert sent_addresses(mail_stub) == [ACME_CONTACT, NEWCOMER_GENERAL]
    body = await campaign(client, president_headers, campaign_id)
    assert body["counts"] == {"pending": 0, "sent": 2, "failed": 0, "skipped": 1}


async def test_a_recipient_attempt_starts_only_once(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    created = await create_campaign(client, president_headers, campaign_world)
    recipient = MailCampaignRecipient(
        campaign_id=UUID(created["id"]),
        company_id=campaign_world.acme_id,
        company_name="Acme AG",
        email=ACME_CONTACT,
    )
    db_session.add(recipient)
    await db_session.commit()
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)
    now = datetime.now(timezone.utc)

    async with sessions() as first, sessions() as second:
        started = [
            await MailCampaignRepository(first).start_attempt(recipient.id, now),
            await MailCampaignRepository(second).start_attempt(recipient.id, now),
        ]

    assert started == [True, False]


async def test_failed_deliveries_are_logged_and_can_be_retried(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    async def reject_newcomer(message: Any) -> None:
        if recipients_of(message) == [NEWCOMER_GENERAL]:
            raise RuntimeError("notifications api down")

    mail_stub.SendMail.side_effect = reject_newcomer
    created = await create_campaign(client, president_headers, campaign_world)
    await client.post(f"{BASE}/{created['id']}/send", headers=president_headers)

    failed = await campaign(client, president_headers, created["id"])

    assert failed["status"] == "PARTIALLY_FAILED"
    assert recipient_states(failed) == [
        ("Acme AG", "SENT", None, 1),
        ("Newcomer AG", "FAILED", "DELIVERY_FAILED", 1),
        ("Silent AG", "SKIPPED", None, 0),
    ]

    mail_stub.SendMail.side_effect = None
    retry = await client.post(
        f"{BASE}/{created['id']}/retry", headers=president_headers
    )
    assert retry.status_code == 200

    retried = await campaign(client, president_headers, created["id"])
    assert retried["status"] == "SENT"
    assert recipient_states(retried) == [
        ("Acme AG", "SENT", None, 1),
        ("Newcomer AG", "SENT", None, 2),
        ("Silent AG", "SKIPPED", None, 0),
    ]
    assert sent_addresses(mail_stub) == [
        ACME_CONTACT,
        NEWCOMER_GENERAL,
        NEWCOMER_GENERAL,
    ]


async def test_repeated_failures_stop_the_campaign_early(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    create_user: Any,
    mail_stub: AsyncMock,
):
    for index in range(5):
        member = await create_user(
            email=f"member{index}@extra.example", company_name=f"Extra {index}"
        )
        await add_profile(
            db_session, member.company_id, general_email=f"info{index}@extra.example"
        )
    mail_stub.SendMail.side_effect = RuntimeError("notifications api down")
    created = await create_campaign(
        client,
        president_headers,
        campaign_world,
        audience={"segments": ["NOT_REGISTERED"]},
    )

    await client.post(f"{BASE}/{created['id']}/send", headers=president_headers)

    body = await campaign(client, president_headers, created["id"])
    assert mail_stub.SendMail.await_count == 5
    assert body["status"] == "PARTIALLY_FAILED"
    errors = [entry["error"] for entry in body["recipients"] if entry["email"]]
    assert errors.count("DELIVERY_FAILED") == 5
    assert errors.count("ABORTED") == 1


async def test_an_interrupted_delivery_resumes_without_sending_twice(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)
    campaign_id = UUID(created["id"])
    now = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
    stored = (
        await db_session.execute(
            select(MailCampaign).where(col(MailCampaign.id) == campaign_id)
        )
    ).scalar_one()
    stored.status = MailCampaignStatus.SENDING
    stored.lease_expires_at = now - ONE_SECOND
    stored.recipients_resolved_at = now - timedelta(minutes=30)
    db_session.add_all(
        [
            stored,
            MailCampaignRecipient(
                campaign_id=campaign_id,
                company_id=campaign_world.acme_id,
                company_name="Acme AG",
                email=ACME_CONTACT,
                source=MailCampaignRecipientSource.CONTACT,
                status=MailCampaignRecipientStatus.SENDING,
                attempts=1,
            ),
            MailCampaignRecipient(
                campaign_id=campaign_id,
                company_id=campaign_world.newcomer_id,
                company_name="Newcomer AG",
                email=NEWCOMER_GENERAL,
                source=MailCampaignRecipientSource.GENERAL_EMAIL,
            ),
        ]
    )
    await db_session.commit()

    resumed = await delivery(db_session, mail_stub, now).run_due()

    assert resumed == 1
    assert sent_addresses(mail_stub) == [NEWCOMER_GENERAL]
    body = await campaign(client, president_headers, created["id"])
    assert body["status"] == "PARTIALLY_FAILED"
    assert recipient_states(body) == [
        ("Acme AG", "FAILED", "INTERRUPTED", 1),
        ("Newcomer AG", "SENT", None, 1),
    ]


async def test_a_running_delivery_is_not_taken_over(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)
    now = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)
    stored = (
        await db_session.execute(
            select(MailCampaign).where(col(MailCampaign.id) == UUID(created["id"]))
        )
    ).scalar_one()
    stored.status = MailCampaignStatus.SENDING
    stored.lease_expires_at = now + timedelta(minutes=5)
    db_session.add(stored)
    await db_session.commit()

    assert await delivery(db_session, mail_stub, now).run_due() == 0
    assert sent_messages(mail_stub) == []
