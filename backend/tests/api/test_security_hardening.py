from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.utils import bounded_filename, safe_suffix
from app.models.user import User
from tests.api.conftest import KpSetup, company_profile_payload, first_member_id

IMPERSONATE_HEADER = "X-Impersonate-User-Id"


@pytest.fixture
async def plain_staff_headers(
    create_user: Callable[..., Awaitable[User]],
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    helper = await create_user(
        email="helper@example.com", is_staff=True, is_company=False
    )
    return {**await auth_headers(helper), **csrf_headers}


async def test_plain_staff_cannot_move_an_admin_into_a_company(
    client: AsyncClient,
    company_user: User,
    create_user: Callable[..., Awaitable[User]],
    plain_staff_headers: dict[str, str],
):
    privileged = await create_user(
        email="privileged@example.com", is_admin=True, is_staff=True
    )

    response = await client.post(
        f"/api/companies/{company_user.company_id}/members",
        json={"user_id": str(privileged.id)},
        headers=plain_staff_headers,
    )

    assert response.status_code == 403


async def test_an_admin_cannot_impersonate_another_admin(
    client: AsyncClient,
    create_user: Callable[..., Awaitable[User]],
    staff_headers: dict[str, str],
):
    other_admin = await create_user(
        email="other-admin@example.com", is_admin=True, is_staff=True
    )

    response = await client.get(
        "/api/user/profile",
        headers={**staff_headers, IMPERSONATE_HEADER: str(other_admin.id)},
    )

    assert response.status_code == 403


async def test_renaming_a_confirmed_company_asks_staff_again(
    client: AsyncClient,
    company_headers: dict[str, str],
    mail_stub: AsyncMock,
):
    response = await client.patch(
        "/api/company/me",
        json={"name": "Totally Different AG"},
        headers=company_headers,
    )
    company = await client.get("/api/company/me", headers=company_headers)

    assert response.status_code == 200
    assert company.json()["confirmed_at"] is None
    mail_stub.SendMail.assert_awaited_once()


async def test_a_company_website_must_be_an_http_url(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.put(
        "/api/company/me/profile",
        json=company_profile_payload(
            kp_contact_user_id=await first_member_id(client, company_headers),
            website="javascript:alert(1)",
        ),
        headers=company_headers,
    )

    assert response.status_code == 422


async def test_a_package_cannot_contain_a_service_that_excludes_it(
    client: AsyncClient, staff_headers: dict[str, str], kp_setup: KpSetup
):
    package = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/services",
        json={"name": "Package"},
        headers=staff_headers,
    )
    await client.patch(
        f"/api/kp/services/{kp_setup.service_id}",
        json={"excluded_service_ids": [package.json()["id"]]},
        headers=staff_headers,
    )

    response = await client.patch(
        f"/api/kp/services/{package.json()['id']}",
        json={"included_services": [{"service_id": kp_setup.service_id}]},
        headers=staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.kp_service_relation_invalid"


@pytest.mark.parametrize(
    ("filename", "suffix"),
    [
        ("logo.PNG", ".png"),
        ("report.pdf", ".pdf"),
        ("no-suffix", ""),
        ("weird.p h p", ""),
        ("long." + "x" * 40, ""),
    ],
)
def test_storage_keys_only_keep_plain_suffixes(filename: str, suffix: str):
    assert safe_suffix(filename) == suffix


def test_stored_filenames_are_bounded():
    assert len(bounded_filename("a" * 1000 + ".pdf")) == 255
    assert bounded_filename("a" * 1000 + ".pdf").endswith(".pdf")
