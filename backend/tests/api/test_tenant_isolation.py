from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.company import CompanyInvite
from app.models.kp_event import (
    KpEventServiceRequirement,
    KpEventServiceRequirementType,
)
from app.models.user import User
from app.services.auth_service import AuthService
from tests.api.conftest import PNG_UPLOAD, KpSetup, company_profile_payload

OWN_COMPANY_EMAIL = "company@example.com"
OWN_TEXT_ANSWER = "Answer of company A"
OWN_NAME_TAG = {
    "first_name": "Ada",
    "last_name": "Lovelace",
    "position": "Engineer",
}
HIJACKED_TEXT_ANSWER = "Answer of company B"
OTHER_COMPANY_NAME = "Beta GmbH"
OTHER_COMPANY_EMAIL = "beta@example.com"
HIJACKED_NAME_TAG = {
    "first_name": "Mallory",
    "last_name": "Intruder",
    "position": "Guest",
}
TEXT_REQUIREMENT_DESCRIPTION = "Describe the booth layout in a few sentences."
FILE_REQUIREMENT_DESCRIPTION = "Upload the company logo for the booth wall."


@dataclass(frozen=True)
class CrossTenantRequest:
    method: str
    url: str
    body: dict[str, Any] | None = None
    upload: bool = False


@dataclass(frozen=True)
class Tenants:
    event_id: str
    upgrade_zone_id: str
    service_id: str
    booking_a: str
    booking_b: str
    booking_service_a: str
    text_requirement_id: str
    file_requirement_id: str
    company_a: str
    headers_a: dict[str, str]
    headers_b: dict[str, str]


@pytest.fixture
async def other_company_user(create_user: Callable[..., Awaitable[User]]) -> User:
    return await create_user(
        email=OTHER_COMPANY_EMAIL, password=None, company_name=OTHER_COMPANY_NAME
    )


@pytest.fixture
async def other_company_headers(
    other_company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(other_company_user), **csrf_headers}


@pytest.fixture
async def tenants(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    company_headers: dict[str, str],
    other_company_headers: dict[str, str],
    staff_headers: dict[str, str],
    kp_setup: KpSetup,
    register_booking: Callable[..., Awaitable[Response]],
) -> Tenants:
    text_requirement = KpEventServiceRequirement(
        service_id=UUID(kp_setup.service_id),
        type=KpEventServiceRequirementType.TEXT,
        name="Booth layout",
        description=TEXT_REQUIREMENT_DESCRIPTION,
    )
    file_requirement = KpEventServiceRequirement(
        service_id=UUID(kp_setup.service_id),
        type=KpEventServiceRequirementType.FILE,
        name="Company logo",
        description=FILE_REQUIREMENT_DESCRIPTION,
    )
    db_session.add_all([text_requirement, file_requirement])
    await db_session.commit()

    upgrade_zone = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/booth-zones",
        json={"name": "Upgrade hall", "capacity": 1, "color": "#AABBCC"},
        headers=staff_headers,
    )
    booking_a = (await register_booking(company_headers, kp_setup)).json()
    booking_b = (await register_booking(other_company_headers, kp_setup)).json()
    booking_service_a = booking_a["services"][0]["id"]
    requirements = f"/api/kp/booking-services/{booking_service_a}/requirements"

    await client.put(
        f"{requirements}/{text_requirement.id}/text",
        json={"text_value": OWN_TEXT_ANSWER},
        headers=company_headers,
    )
    await client.post(
        f"{requirements}/{file_requirement.id}/file",
        files={"file": PNG_UPLOAD},
        headers=company_headers,
    )
    await client.put(
        f"/api/kp/bookings/{booking_a['id']}/nametags",
        json={"name_tags": [OWN_NAME_TAG]},
        headers=company_headers,
    )

    return Tenants(
        event_id=kp_setup.event_id,
        upgrade_zone_id=upgrade_zone.json()["id"],
        service_id=kp_setup.service_id,
        booking_a=booking_a["id"],
        booking_b=booking_b["id"],
        booking_service_a=booking_service_a,
        text_requirement_id=str(text_requirement.id),
        file_requirement_id=str(file_requirement.id),
        company_a=str(company_user.company_id),
        headers_a=company_headers,
        headers_b=other_company_headers,
    )


def cross_tenant_requests(tenants: Tenants) -> dict[str, CrossTenantRequest]:
    booking = f"/api/kp/bookings/{tenants.booking_a}"
    text = (
        f"/api/kp/booking-services/{tenants.booking_service_a}"
        f"/requirements/{tenants.text_requirement_id}/text"
    )
    file = (
        f"/api/kp/booking-services/{tenants.booking_service_a}"
        f"/requirements/{tenants.file_requirement_id}/file"
    )
    staff_file = (
        f"/api/kp/staff/booking-services/{tenants.booking_service_a}"
        f"/requirements/{tenants.file_requirement_id}/file"
    )
    return {
        "add-services": CrossTenantRequest(
            "POST",
            f"{booking}/services",
            {"services": [{"service_id": tenants.service_id, "quantity": 1}]},
        ),
        "read-waitlist": CrossTenantRequest("GET", f"{booking}/upgrade-waitlist"),
        "write-waitlist": CrossTenantRequest(
            "PUT",
            f"{booking}/upgrade-waitlist",
            {"target_booth_zone_ids": [tenants.upgrade_zone_id]},
        ),
        "switch-zone": CrossTenantRequest(
            "POST",
            f"{booking}/switch-zone",
            {"booth_zone_id": tenants.upgrade_zone_id},
        ),
        "change-status": CrossTenantRequest(
            "PATCH", f"{booking}/status", {"status": "CANCELLED"}
        ),
        "finalize": CrossTenantRequest(
            "PATCH", f"{booking}/status", {"status": "FINALIZED"}
        ),
        "download-nametags": CrossTenantRequest("GET", f"{booking}/nametags/download"),
        "read-nametags": CrossTenantRequest("GET", f"{booking}/nametags"),
        "write-nametags": CrossTenantRequest(
            "PUT",
            f"{booking}/nametags",
            {"name_tags": [HIJACKED_NAME_TAG]},
        ),
        "staff-read-nametags": CrossTenantRequest(
            "GET", f"/api/kp/staff/bookings/{tenants.booking_a}/nametags"
        ),
        "staff-read-waitlist": CrossTenantRequest(
            "GET", f"/api/kp/staff/bookings/{tenants.booking_a}/upgrade-waitlist"
        ),
        "read-text": CrossTenantRequest("GET", text),
        "write-text": CrossTenantRequest(
            "PUT", text, {"text_value": HIJACKED_TEXT_ANSWER}
        ),
        "read-file": CrossTenantRequest("GET", file),
        "upload-file": CrossTenantRequest("POST", file, upload=True),
        "delete-file": CrossTenantRequest("DELETE", file),
        "download-file": CrossTenantRequest("GET", f"{file}/download"),
        "staff-read-file": CrossTenantRequest("GET", staff_file),
        "staff-read-booking": CrossTenantRequest(
            "GET", f"/api/kp/events/{tenants.event_id}/bookings/{tenants.booking_a}"
        ),
    }


CROSS_TENANT_CASES = [
    "add-services",
    "change-status",
    "delete-file",
    "download-file",
    "download-nametags",
    "finalize",
    "read-file",
    "read-nametags",
    "read-text",
    "read-waitlist",
    "staff-read-booking",
    "staff-read-file",
    "staff-read-nametags",
    "staff-read-waitlist",
    "switch-zone",
    "upload-file",
    "write-nametags",
    "write-text",
    "write-waitlist",
]


async def snapshot_company_a(client: AsyncClient, tenants: Tenants) -> dict[str, Any]:
    requirements = f"/api/kp/booking-services/{tenants.booking_service_a}/requirements"
    booking = await client.get(
        f"/api/kp/events/{tenants.event_id}/my-booking", headers=tenants.headers_a
    )
    text = await client.get(
        f"{requirements}/{tenants.text_requirement_id}/text", headers=tenants.headers_a
    )
    file = await client.get(
        f"{requirements}/{tenants.file_requirement_id}/file", headers=tenants.headers_a
    )
    name_tags = await client.get(
        f"/api/kp/bookings/{tenants.booking_a}/nametags", headers=tenants.headers_a
    )
    return {
        "booking": booking.json(),
        "text": text.json(),
        "file": file.json(),
        "name_tags": name_tags.json(),
    }


async def latest_invite_token(db_session: AsyncSession) -> str:
    result = await db_session.execute(select(CompanyInvite))
    return result.scalars().one().token


async def test_company_a_snapshot_is_complete(client: AsyncClient, tenants: Tenants):
    snapshot = await snapshot_company_a(client, tenants)

    assert snapshot["booking"]["id"] == tenants.booking_a
    assert snapshot["text"]["text_value"] == OWN_TEXT_ANSWER
    assert snapshot["file"]["stored_file"]["original_filename"] == PNG_UPLOAD[0]
    assert [tag["first_name"] for tag in snapshot["name_tags"]] == ["Ada"]


@pytest.mark.parametrize("case", CROSS_TENANT_CASES)
async def test_other_company_cannot_touch_booking(
    client: AsyncClient, tenants: Tenants, case: str
):
    before = await snapshot_company_a(client, tenants)
    request = cross_tenant_requests(tenants)[case]

    response = await client.request(
        request.method,
        request.url,
        json=request.body,
        files={"file": PNG_UPLOAD} if request.upload else None,
        headers=tenants.headers_b,
    )

    assert response.status_code in {403, 404}
    assert await snapshot_company_a(client, tenants) == before


async def test_cross_tenant_cases_cover_every_booking_endpoint(tenants: Tenants):
    assert sorted(cross_tenant_requests(tenants)) == CROSS_TENANT_CASES


async def test_my_booking_stays_scoped_to_the_own_company(
    client: AsyncClient, tenants: Tenants
):
    response = await client.get(
        f"/api/kp/events/{tenants.event_id}/my-booking", headers=tenants.headers_b
    )

    assert response.status_code == 200
    assert response.json()["id"] == tenants.booking_b


async def test_invite_cannot_be_accepted_by_a_user_of_another_company(
    client: AsyncClient,
    db_session: AsyncSession,
    tenants: Tenants,
    other_company_user: User,
):
    await client.post(
        "/api/company/invite",
        json={"email": other_company_user.email},
        headers=tenants.headers_a,
    )
    token = await latest_invite_token(db_session)

    response = await client.post(
        f"/api/company/invite/{token}/accept", headers=tenants.headers_b
    )
    members = await client.get("/api/company/me/members", headers=tenants.headers_a)

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"
    assert [member["email"] for member in members.json()] == [OWN_COMPANY_EMAIL]


async def test_company_members_are_scoped_to_the_own_company(
    client: AsyncClient, tenants: Tenants
):
    response = await client.get("/api/company/me/members", headers=tenants.headers_b)

    assert response.status_code == 200
    assert [member["email"] for member in response.json()] == [OTHER_COMPANY_EMAIL]


@pytest.mark.parametrize("suffix", ["users", "with-users"])
async def test_company_user_cannot_read_another_company(
    client: AsyncClient, tenants: Tenants, suffix: str
):
    response = await client.get(
        f"/api/company/{tenants.company_a}/{suffix}", headers=tenants.headers_b
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_venue_map_own_booking_is_scoped_to_the_own_company(
    client: AsyncClient, tenants: Tenants
):
    response = await client.get(
        f"/api/kp/events/{tenants.event_id}/venue", headers=tenants.headers_b
    )

    assert response.status_code == 200
    assert response.json()["own_booking"]["booking_id"] == tenants.booking_b


@pytest.mark.parametrize(
    "path",
    ["/api/users", "/api/users/{user_id}", "/api/companies"],
)
async def test_company_user_cannot_read_the_management_lists(
    client: AsyncClient, tenants: Tenants, company_user: User, path: str
):
    response = await client.get(
        path.format(user_id=company_user.id), headers=tenants.headers_b
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
async def test_company_user_cannot_manage_another_user(
    client: AsyncClient, tenants: Tenants, company_user: User, method: str
):
    response = await client.request(
        method,
        f"/api/users/{company_user.id}",
        json={"first_name": "Hijacked"} if method == "PATCH" else None,
        headers=tenants.headers_b,
    )
    profile = await client.get("/api/user/profile", headers=tenants.headers_a)

    assert response.status_code == 403
    assert profile.json()["first_name"] != "Hijacked"


async def test_company_user_cannot_add_members_to_a_company(
    client: AsyncClient, tenants: Tenants, other_company_user: User
):
    response = await client.post(
        f"/api/companies/{tenants.company_a}/members",
        json={"user_id": str(other_company_user.id)},
        headers=tenants.headers_b,
    )
    members = await client.get("/api/company/me/members", headers=tenants.headers_a)

    assert response.status_code == 403
    assert [member["email"] for member in members.json()] == [OWN_COMPANY_EMAIL]


async def test_company_user_cannot_rename_another_company(
    client: AsyncClient, tenants: Tenants
):
    response = await client.patch(
        f"/api/companies/{tenants.company_a}",
        json={"name": "Hijacked AG"},
        headers=tenants.headers_b,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"


async def test_company_profile_is_scoped_to_the_own_company(
    client: AsyncClient, tenants: Tenants
):
    await client.put(
        "/api/company/me/profile",
        json=company_profile_payload(billing_city="Acme city"),
        headers=tenants.headers_a,
    )

    response = await client.get("/api/company/me/profile", headers=tenants.headers_b)

    assert response.status_code == 200
    assert response.json()["billing_city"] == "Zurich"
    assert response.json()["company_id"] != tenants.company_a


async def test_company_profile_of_another_company_is_refused_for_companies(
    client: AsyncClient, tenants: Tenants
):
    read = await client.get(
        f"/api/company/{tenants.company_a}/profile", headers=tenants.headers_b
    )
    write = await client.put(
        f"/api/company/{tenants.company_a}/profile",
        json=company_profile_payload(billing_city="Hijacked"),
        headers=tenants.headers_b,
    )
    own = await client.get("/api/company/me/profile", headers=tenants.headers_a)

    assert read.status_code == 403
    assert write.status_code == 403
    assert own.json()["billing_city"] == "Zurich"


async def test_logo_of_another_company_cannot_be_deleted(
    client: AsyncClient, tenants: Tenants
):
    await client.post(
        "/api/company/me/profile/logo",
        files={"file": PNG_UPLOAD},
        headers=tenants.headers_a,
    )

    await client.delete("/api/company/me/profile/logo", headers=tenants.headers_b)
    via_staff_route = await client.delete(
        f"/api/company/{tenants.company_a}/profile/logo", headers=tenants.headers_b
    )
    own = await client.get("/api/company/me/profile", headers=tenants.headers_a)

    assert via_staff_route.status_code == 403
    assert own.json()["logo_url"] is not None


async def test_login_link_logs_in_its_own_company_user_only(
    client: AsyncClient,
    auth_service: AuthService,
    other_company_user: User,
    csrf_headers: dict[str, str],
):
    login_url = await auth_service.create_login_link(other_company_user, "/")

    link_response = await client.get(f"/api/auth/link/{login_url.rsplit('/', 1)[1]}")
    client.cookies.update(link_response.cookies)
    token = (await client.post("/api/auth/refresh", headers=csrf_headers)).json()
    me = await client.get(
        "/api/user/me",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            **csrf_headers,
        },
    )

    assert me.json()["email"] == OTHER_COMPANY_EMAIL


async def test_company_user_cannot_read_mail_templates(
    client: AsyncClient, tenants: Tenants
):
    response = await client.get("/api/mail-templates", headers=tenants.headers_b)

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_allowed"
