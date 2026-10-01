from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.models.auth_tokens import LoginLinkToken
from app.models.kp_event import KpBookingStatus
from app.models.user import User
from tests.api.conftest import decoded_subject
from tests.api.mail_campaign_helpers import (
    ACME_CONTACT,
    NEWCOMER_GENERAL,
    CampaignWorld,
    add_booking,
    campaign_payload,
    create_campaign,
    recipients_of,
    sent_addresses,
    sent_messages,
)

BASE = "/api/mail-campaigns"


async def login_link_count(db_session: AsyncSession) -> int:
    result = await db_session.execute(select(func.count()).select_from(LoginLinkToken))
    return result.scalar_one()


async def send(
    client: AsyncClient, headers: dict[str, str], campaign_id: str
) -> dict[str, Any]:
    response = await client.post(f"{BASE}/{campaign_id}/send", headers=headers)
    assert response.status_code == 200, response.text
    return (await client.get(f"{BASE}/{campaign_id}", headers=headers)).json()


@pytest.fixture
async def plain_staff_headers(
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(staff_user), **csrf_headers}


async def test_staff_without_the_president_role_cannot_manage_campaigns(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.get(BASE, headers=plain_staff_headers)

    assert response.status_code == 403


async def test_a_new_campaign_is_a_listed_draft(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    created = await create_campaign(client, president_headers, campaign_world)

    assert created["status"] == "DRAFT"
    assert created["audience"]["segments"] == ["NOT_REGISTERED", "REGISTERED"]
    assert created["recipients"] == []
    listed = (await client.get(BASE, headers=president_headers)).json()
    assert [(item["id"], item["event_name"]) for item in listed] == [
        (created["id"], "Kontaktparty")
    ]


async def test_unknown_variables_are_rejected_on_save(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    response = await client.post(
        BASE,
        json=campaign_payload(campaign_world, body_de="<p>{{ password }}</p>"),
        headers=president_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.mail_template_invalid"
    assert response.json()["details"] == {"field": "body_de", "variable": "password"}


async def test_the_variable_list_matches_the_renderer(
    client: AsyncClient, president_headers: dict[str, str]
):
    response = await client.get(f"{BASE}/variables", headers=president_headers)

    assert "company_name" in response.json()
    assert "login_url" in response.json()


async def test_the_company_list_offers_every_company(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    response = await client.get(f"{BASE}/companies", headers=president_headers)

    assert [company["name"] for company in response.json()] == [
        "Acme AG",
        "Newcomer AG",
        "Silent AG",
    ]


async def test_the_audience_preview_shows_addresses_and_skipped_companies(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    response = await client.post(
        f"{BASE}/audience",
        json={
            "event_id": campaign_world.event_id,
            "audience": {"segments": ["NOT_REGISTERED", "REGISTERED"]},
        },
        headers=president_headers,
    )

    body = response.json()
    assert (body["recipient_count"], body["skipped_count"]) == (2, 1)
    assert [
        (entry["company_name"], entry["email"], entry["source"], entry["skip_reason"])
        for entry in body["recipients"]
    ] == [
        ("Acme AG", ACME_CONTACT, "CONTACT", None),
        ("Newcomer AG", NEWCOMER_GENERAL, "GENERAL_EMAIL", None),
        ("Silent AG", None, None, "NO_ADDRESS"),
    ]


async def test_the_audience_preview_applies_manual_lists(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    response = await client.post(
        f"{BASE}/audience",
        json={
            "event_id": campaign_world.event_id,
            "audience": {
                "segments": ["NOT_REGISTERED"],
                "include_company_ids": [str(campaign_world.acme_id)],
                "exclude_company_ids": [str(campaign_world.silent_id)],
            },
        },
        headers=president_headers,
    )

    assert [
        (entry["company_name"], entry["manually_included"])
        for entry in response.json()["recipients"]
    ] == [("Acme AG", True), ("Newcomer AG", False)]


async def test_the_render_preview_uses_a_sample_company_without_login_links(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    links_before = await login_link_count(db_session)

    response = await client.post(
        f"{BASE}/render",
        json={
            **campaign_payload(campaign_world),
            "company_id": str(campaign_world.acme_id),
        },
        headers=president_headers,
    )

    body = response.json()
    assert body["subject"] == (
        "Anmeldung für Kontaktparty / Registration for Kontaktparty"
    )
    assert "Hallo Test User" in body["text"]
    assert "/login" in body["text"]
    assert await login_link_count(db_session) == links_before


async def test_a_test_mail_only_goes_to_the_current_user(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    response = await client.post(
        f"{BASE}/test-send",
        json={
            **campaign_payload(campaign_world),
            "company_id": str(campaign_world.acme_id),
        },
        headers=president_headers,
    )

    assert response.status_code == 200
    assert sent_addresses(mail_stub) == ["president@example.com"]


async def test_a_failed_test_mail_reports_the_mail_service(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    mail_stub.SendMail.side_effect = RuntimeError("notifications api down")

    response = await client.post(
        f"{BASE}/test-send",
        json=campaign_payload(campaign_world),
        headers=president_headers,
    )

    assert response.status_code == 503
    assert response.json()["code"] == "error.mail_unavailable"


async def test_send_now_mails_the_primary_contacts_and_logs_every_company(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)

    campaign = await send(client, president_headers, created["id"])

    assert campaign["status"] == "SENT"
    assert campaign["counts"] == {"pending": 0, "sent": 2, "failed": 0, "skipped": 1}
    assert sent_addresses(mail_stub) == [ACME_CONTACT, NEWCOMER_GENERAL]
    assert all(len(recipients_of(m)) == 1 for m in sent_messages(mail_stub))
    assert [
        (entry["company_name"], entry["email"], entry["status"], entry["skip_reason"])
        for entry in campaign["recipients"]
    ] == [
        ("Acme AG", ACME_CONTACT, "SENT", None),
        ("Newcomer AG", NEWCOMER_GENERAL, "SENT", None),
        ("Silent AG", None, "SKIPPED", "NO_ADDRESS"),
    ]
    assert all(entry["sent_at"] for entry in campaign["recipients"] if entry["email"])


async def test_contacts_get_a_login_link_and_general_addresses_the_login_page(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)

    await send(client, president_headers, created["id"])

    texts = {
        recipients_of(message)[0]: message.plain_text
        for message in sent_messages(mail_stub)
    }
    assert "/auth/link/" in texts[ACME_CONTACT]
    assert "Hallo Test User" in texts[ACME_CONTACT]
    assert "/auth/link/" not in texts[NEWCOMER_GENERAL]
    assert "/login" in texts[NEWCOMER_GENERAL]
    assert "Hallo Newcomer AG" in texts[NEWCOMER_GENERAL]
    assert decoded_subject(sent_messages(mail_stub)[0]) == (
        "Anmeldung für Kontaktparty / Registration for Kontaktparty"
    )


async def test_a_german_only_campaign_sends_a_german_subject(
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
        audience={"segments": ["REGISTERED"]},
    )

    await send(client, president_headers, created["id"])

    [message] = sent_messages(mail_stub)
    assert decoded_subject(message) == "Anmeldung für Kontaktparty"
    assert "register" not in message.plain_text


async def test_the_audience_is_evaluated_when_the_campaign_is_sent(
    client: AsyncClient,
    db_session: AsyncSession,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(
        client,
        president_headers,
        campaign_world,
        audience={"segments": ["NOT_REGISTERED"]},
    )
    await add_booking(
        db_session, campaign_world, campaign_world.newcomer_id, KpBookingStatus.OFFERED
    )

    campaign = await send(client, president_headers, created["id"])

    assert sent_addresses(mail_stub) == []
    assert [entry["company_name"] for entry in campaign["recipients"]] == ["Silent AG"]


async def test_a_sent_campaign_is_locked(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)
    await send(client, president_headers, created["id"])

    again = await client.post(f"{BASE}/{created['id']}/send", headers=president_headers)
    edit = await client.put(
        f"{BASE}/{created['id']}",
        json=campaign_payload(campaign_world),
        headers=president_headers,
    )
    delete = await client.delete(f"{BASE}/{created['id']}", headers=president_headers)

    assert [again.status_code, edit.status_code, delete.status_code] == [409] * 3
    assert again.json()["code"] == "error.mail_campaign_locked"
    assert len(sent_messages(mail_stub)) == 2


async def test_a_sent_campaign_can_be_duplicated_into_a_draft(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    created = await create_campaign(client, president_headers, campaign_world)
    await send(client, president_headers, created["id"])

    response = await client.post(
        f"{BASE}/{created['id']}/duplicate", headers=president_headers
    )

    copy = response.json()
    assert copy["status"] == "DRAFT"
    assert copy["name"] == "Registration reminder (copy)"
    assert copy["body_de"] == created["body_de"]
    assert copy["audience"] == created["audience"]
    assert copy["recipients"] == []


async def test_a_schedule_in_the_past_is_rejected(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    created = await create_campaign(client, president_headers, campaign_world)

    response = await client.post(
        f"{BASE}/{created['id']}/schedule",
        json={"scheduled_at": "2020-01-01T09:00"},
        headers=president_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.mail_campaign_schedule_in_past"


@pytest.mark.parametrize(
    ("local", "utc"),
    [
        ("2030-07-01T09:00", "2030-07-01T07:00:00Z"),
        ("2030-12-01T09:00", "2030-12-01T08:00:00Z"),
        ("2030-12-01T09:00:00+00:00", "2030-12-01T09:00:00Z"),
    ],
)
async def test_schedules_are_read_as_zurich_time(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    local: str,
    utc: str,
):
    created = await create_campaign(client, president_headers, campaign_world)

    response = await client.post(
        f"{BASE}/{created['id']}/schedule",
        json={"scheduled_at": local},
        headers=president_headers,
    )

    assert response.json()["status"] == "SCHEDULED"
    assert response.json()["scheduled_at"].replace("+00:00", "Z") == utc


async def test_a_scheduled_campaign_can_be_edited_cancelled_and_deleted(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
    mail_stub: AsyncMock,
):
    created = await create_campaign(client, president_headers, campaign_world)
    url = f"{BASE}/{created['id']}"
    await client.post(
        f"{url}/schedule",
        json={"scheduled_at": "2030-07-01T09:00"},
        headers=president_headers,
    )

    edited = await client.put(
        url,
        json=campaign_payload(campaign_world, name="Final reminder"),
        headers=president_headers,
    )
    assert (edited.json()["name"], edited.json()["status"]) == (
        "Final reminder",
        "SCHEDULED",
    )

    cancelled = await client.post(f"{url}/unschedule", headers=president_headers)
    assert cancelled.json()["status"] == "DRAFT"
    assert cancelled.json()["scheduled_at"] is None

    deleted = await client.delete(url, headers=president_headers)
    assert deleted.status_code == 200
    assert (await client.get(url, headers=president_headers)).status_code == 404
    assert sent_messages(mail_stub) == []


async def test_retry_is_only_possible_after_failures(
    client: AsyncClient,
    president_headers: dict[str, str],
    campaign_world: CampaignWorld,
):
    created = await create_campaign(client, president_headers, campaign_world)

    response = await client.post(
        f"{BASE}/{created['id']}/retry", headers=president_headers
    )

    assert response.status_code == 409


async def test_unknown_campaigns_are_not_found(
    client: AsyncClient, president_headers: dict[str, str]
):
    response = await client.get(
        f"{BASE}/00000000-0000-0000-0000-000000000000", headers=president_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.mail_campaign_not_found"
