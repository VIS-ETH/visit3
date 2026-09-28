from typing import Any

import pytest
from httpx import AsyncClient

from tests.api.conftest import kp_payload

TERMS_URL = "https://vis.ethz.ch/kp/agb"
NOTIFICATION_EMAIL = "kp-notify@vis.ethz.ch"


def settings_payload(name: str, **overrides: Any) -> dict[str, Any]:
    return {
        **kp_payload(name),
        "vat_rate_percent": 7.7,
        "terms_url": TERMS_URL,
        "notification_email": NOTIFICATION_EMAIL,
        "finalization_reminder_days": 10,
        **overrides,
    }


async def test_event_without_settings_uses_the_standard_vat_rate(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.post(
        "/api/kp/create", json=kp_payload("Defaults"), headers=staff_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["vat_rate_percent"] == 8.1
    assert body["terms_url"] is None
    assert body["notification_email"] is None
    assert body["finalization_reminder_days"] == 3


async def test_staff_settings_endpoint_returns_the_stored_settings(
    client: AsyncClient, staff_headers: dict[str, str]
):
    created = await client.post(
        "/api/kp/create", json=settings_payload("Settings"), headers=staff_headers
    )
    event_id = created.json()["id"]

    response = await client.get(
        f"/api/kp/events/{event_id}/settings", headers=staff_headers
    )

    assert response.status_code == 200
    assert response.json() == {
        **created.json(),
        "vat_rate_percent": 7.7,
        "terms_url": TERMS_URL,
        "notification_email": NOTIFICATION_EMAIL,
        "finalization_reminder_days": 10,
    }


async def test_company_visible_event_hides_the_notification_email(
    client: AsyncClient,
    staff_headers: dict[str, str],
    company_headers: dict[str, str],
):
    created = await client.post(
        "/api/kp/create", json=settings_payload("Public"), headers=staff_headers
    )
    event_id = created.json()["id"]

    response = await client.get(f"/api/kp/events/{event_id}", headers=company_headers)

    assert response.status_code == 200
    body = response.json()
    assert "notification_email" not in body
    assert body["vat_rate_percent"] == 7.7
    assert body["terms_url"] == TERMS_URL


async def test_updating_the_vat_rate_and_clearing_the_terms_url(
    client: AsyncClient, staff_headers: dict[str, str]
):
    created = await client.post(
        "/api/kp/create", json=settings_payload("Updated"), headers=staff_headers
    )
    event_id = created.json()["id"]

    response = await client.patch(
        f"/api/kp/events/{event_id}",
        json={"vat_rate_percent": 2.6, "terms_url": ""},
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["vat_rate_percent"] == 2.6
    assert response.json()["terms_url"] is None
    assert response.json()["notification_email"] == NOTIFICATION_EMAIL


async def test_cloned_event_keeps_the_settings(
    client: AsyncClient, staff_headers: dict[str, str]
):
    created = await client.post(
        "/api/kp/create", json=settings_payload("Original"), headers=staff_headers
    )

    response = await client.post(
        f"/api/kp/events/{created.json()['id']}/clone",
        json=settings_payload("Clone"),
        headers=staff_headers,
    )

    assert response.status_code == 200
    assert response.json()["vat_rate_percent"] == 7.7
    assert response.json()["terms_url"] == TERMS_URL


@pytest.mark.parametrize("terms_url", ["not-a-url", "ftp://vis.ethz.ch/agb"])
async def test_terms_url_must_be_an_http_url(
    client: AsyncClient, staff_headers: dict[str, str], terms_url: str
):
    response = await client.post(
        "/api/kp/create",
        json=settings_payload("Bad terms", terms_url=terms_url),
        headers=staff_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "error.validation_failed"
    assert body["detail"] == "validation.invalid_url"
    assert body["fieldErrors"][0]["field"] == "terms_url"


@pytest.mark.parametrize("vat_rate_percent", [-1, 100.1])
async def test_vat_rate_outside_the_allowed_range_is_rejected(
    client: AsyncClient, staff_headers: dict[str, str], vat_rate_percent: float
):
    response = await client.post(
        "/api/kp/create",
        json=settings_payload("Bad rate", vat_rate_percent=vat_rate_percent),
        headers=staff_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "validation.out_of_range"
    assert response.json()["fieldErrors"][0]["field"] == "vat_rate_percent"


async def test_vat_rate_is_limited_to_one_decimal(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.post(
        "/api/kp/create",
        json=settings_payload("Too precise", vat_rate_percent=8.15),
        headers=staff_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "validation.invalid_number"


async def test_notification_email_must_be_an_email_address(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.post(
        "/api/kp/create",
        json=settings_payload("Bad mail", notification_email="not-an-email"),
        headers=staff_headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "validation.invalid_email"
