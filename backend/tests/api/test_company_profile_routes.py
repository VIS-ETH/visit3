from collections.abc import Awaitable, Callable

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import MANDATORY_PROFILE_FIELDS
from app.models.industry import Industry
from app.models.user import User
from tests.api.conftest import PNG_UPLOAD, company_profile_payload

JPEG_UPLOAD = ("logo.jpg", b"\xff\xd8\xff" + b"\x00" * 32, "image/jpeg")
PROFILE = "/api/company/me/profile"
LOGO = "/api/company/me/profile/logo"


@pytest.fixture
async def industry(db_session: AsyncSession) -> Industry:
    industry = Industry(name="Software")
    db_session.add(industry)
    await db_session.commit()
    return industry


@pytest.fixture
async def unconfirmed_company_user(
    create_user: Callable[..., Awaitable[User]],
) -> User:
    return await create_user(
        email="unconfirmed@example.com",
        user_confirmed=False,
        company_name="Pending AG",
    )


@pytest.fixture
async def unconfirmed_headers(
    unconfirmed_company_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(unconfirmed_company_user), **csrf_headers}


async def test_empty_profile_lists_every_mandatory_field(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.get(PROFILE, headers=company_headers)

    assert response.status_code == 200
    assert response.json()["id"] is None
    assert response.json()["profile_complete"] is False
    assert response.json()["missing_profile_fields"] == list(MANDATORY_PROFILE_FIELDS)


async def test_my_company_reports_the_profile_state(
    client: AsyncClient,
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    before = await client.get("/api/company/me", headers=company_headers)
    await complete_company_profile(company_headers)
    after = await client.get("/api/company/me", headers=company_headers)

    assert before.json()["profile_complete"] is False
    assert before.json()["missing_profile_fields"] == list(MANDATORY_PROFILE_FIELDS)
    assert after.json()["profile_complete"] is True
    assert after.json()["missing_profile_fields"] == []
    assert after.json()["name"] == "Acme AG"


@pytest.mark.parametrize(
    ("overrides", "bookable"),
    [({}, True), ({"description": ""}, True), ({"billing_city": ""}, False)],
)
async def test_only_the_description_may_wait_until_after_the_booking(
    client: AsyncClient,
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
    overrides: dict[str, object],
    bookable: bool,
):
    await complete_company_profile(company_headers, **overrides)

    response = await client.get("/api/company/me", headers=company_headers)

    assert response.json()["profile_bookable"] is bookable


async def test_complete_profile_is_stored_and_marked_complete(
    company_headers: dict[str, str],
    industry: Industry,
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    response = await complete_company_profile(
        company_headers,
        billing_country="ch",
        languages=["ENGLISH", "FRENCH"],
        offers_theses=True,
        employee_count_worldwide=120,
        industry_ids=[str(industry.id)],
    )

    assert response.status_code == 200
    assert response.json()["billing_country"] == "CH"
    assert response.json()["languages"] == ["ENGLISH", "FRENCH"]
    assert response.json()["offers_theses"] is True
    assert response.json()["employee_count_worldwide"] == 120
    assert [entry["name"] for entry in response.json()["industries"]] == ["Software"]
    assert response.json()["profile_complete"] is True
    assert response.json()["profile_completed_at"] is not None
    assert "shipping_address" not in response.json()


async def test_incomplete_profile_keeps_the_completion_timestamp_empty(
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    response = await complete_company_profile(company_headers, billing_city="")

    assert response.json()["missing_profile_fields"] == ["billing_city"]
    assert response.json()["profile_completed_at"] is None


async def test_the_completion_timestamp_marks_the_first_completion(
    company_headers: dict[str, str],
    complete_company_profile: Callable[..., Awaitable[Response]],
):
    first = await complete_company_profile(company_headers)

    second = await complete_company_profile(company_headers, billing_city="Bern")

    assert first.json()["profile_completed_at"] is not None
    assert second.json()["profile_completed_at"] == first.json()["profile_completed_at"]


async def test_profile_accepts_a_description_of_a_booklet_page(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.put(
        PROFILE,
        json=company_profile_payload(description="x" * 2500),
        headers=company_headers,
    )

    assert response.status_code == 200
    assert len(response.json()["description"]) == 2500


async def test_profile_rejects_a_description_over_the_limit(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.put(
        PROFILE,
        json=company_profile_payload(description="x" * 2501),
        headers=company_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "error.validation_failed"


async def test_profile_rejects_an_unknown_industry(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.put(
        PROFILE,
        json=company_profile_payload(
            industry_ids=["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
        ),
        headers=company_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.industry_not_found"


async def test_profile_rejects_a_contact_user_of_another_company(
    client: AsyncClient,
    company_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
):
    outsider = await create_user(email="outsider@example.com", company_name="Other AG")

    response = await client.put(
        PROFILE,
        json=company_profile_payload(kp_contact_user_id=str(outsider.id)),
        headers=company_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.company_user_not_found"


async def test_profile_without_a_contact_member_is_incomplete(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.put(
        PROFILE, json=company_profile_payload(), headers=company_headers
    )

    assert response.status_code == 200
    assert response.json()["missing_profile_fields"] == ["kp_contact_user_id"]
    assert response.json()["kp_contact_user"] is None


async def test_profile_returns_the_contact_member_and_the_general_contact(
    client: AsyncClient,
    db_session: AsyncSession,
    company_user: User,
    company_headers: dict[str, str],
    create_user: Callable[..., Awaitable[User]],
):
    colleague = await create_user(
        email="grace@example.com",
        first_name="Grace",
        last_name="Hopper",
        phone_number="+41 44 111 11 11",
    )
    colleague.company_id = company_user.company_id
    db_session.add(colleague)
    await db_session.commit()

    response = await client.put(
        PROFILE,
        json=company_profile_payload(
            kp_contact_user_id=str(colleague.id),
            general_email="info@acme.example",
            general_phone="+41 44 000 00 00",
        ),
        headers=company_headers,
    )

    assert response.status_code == 200
    assert response.json()["general_email"] == "info@acme.example"
    assert response.json()["general_phone"] == "+41 44 000 00 00"
    assert response.json()["kp_contact_user"] == {
        "id": str(colleague.id),
        "email": "grace@example.com",
        "first_name": "Grace",
        "last_name": "Hopper",
        "phone_number": "+41 44 111 11 11",
    }
    assert response.json()["profile_complete"] is True


async def test_logo_upload_replace_and_delete(
    client: AsyncClient, company_headers: dict[str, str]
):
    uploaded = await client.post(
        LOGO, files={"file": PNG_UPLOAD}, headers=company_headers
    )
    replaced = await client.post(
        LOGO, files={"file": JPEG_UPLOAD}, headers=company_headers
    )
    deleted = await client.delete(LOGO, headers=company_headers)
    after = await client.get(PROFILE, headers=company_headers)

    assert uploaded.status_code == 200
    assert uploaded.json()["logo_url"] == "https://storage.test/download"
    assert replaced.status_code == 200
    assert replaced.json()["logo_url"] == "https://storage.test/download"
    assert deleted.json()["logo_url"] is None
    assert after.json()["logo_url"] is None


async def test_logo_upload_keeps_a_single_stored_file(
    client: AsyncClient, company_headers: dict[str, str], storage_service
):
    await client.post(LOGO, files={"file": PNG_UPLOAD}, headers=company_headers)
    await client.post(LOGO, files={"file": JPEG_UPLOAD}, headers=company_headers)

    assert storage_service.delete_object.await_count == 1


async def test_logo_upload_rejects_a_gif(
    client: AsyncClient, company_headers: dict[str, str], storage_service
):
    storage_service.validate_image_file.side_effect = None
    gif = ("logo.gif", b"GIF89a" + b"\x00" * 32, "image/gif")

    await client.post(LOGO, files={"file": gif}, headers=company_headers)

    assert storage_service.validate_image_file.call_args.kwargs[
        "allowed_mime_types"
    ] == {"image/png", "image/jpeg", "image/webp"}


async def test_logo_delete_without_a_logo_is_accepted(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.delete(LOGO, headers=company_headers)

    assert response.status_code == 200
    assert response.json()["logo_url"] is None


async def test_staff_can_read_and_edit_the_profile_of_any_company(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
):
    await client.put(PROFILE, json=company_profile_payload(), headers=company_headers)
    staff_profile = f"/api/company/{company_user.company_id}/profile"

    read = await client.get(staff_profile, headers=staff_headers)
    written = await client.put(
        staff_profile,
        json=company_profile_payload(billing_city="Bern"),
        headers=staff_headers,
    )
    company_view = await client.get(PROFILE, headers=company_headers)

    assert read.status_code == 200
    assert read.json()["billing_city"] == "Zurich"
    assert written.json()["billing_city"] == "Bern"
    assert company_view.json()["billing_city"] == "Bern"


async def test_staff_can_replace_and_remove_the_logo_of_any_company(
    client: AsyncClient,
    company_user: User,
    company_headers: dict[str, str],
    staff_headers: dict[str, str],
):
    staff_logo = f"/api/company/{company_user.company_id}/profile/logo"

    uploaded = await client.post(
        staff_logo, files={"file": PNG_UPLOAD}, headers=staff_headers
    )
    company_view = await client.get(PROFILE, headers=company_headers)
    removed = await client.delete(staff_logo, headers=staff_headers)

    assert uploaded.status_code == 200
    assert uploaded.json()["logo_url"] is not None
    assert company_view.json()["logo_url"] == uploaded.json()["logo_url"]
    assert removed.status_code == 200
    assert removed.json()["logo_url"] is None


async def test_staff_logo_upload_for_an_unknown_company_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.post(
        "/api/company/3fa85f64-5717-4562-b3fc-2c963f66afa6/profile/logo",
        files={"file": PNG_UPLOAD},
        headers=staff_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.company_not_found"


async def test_staff_profile_of_an_unknown_company_is_not_found(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.get(
        "/api/company/3fa85f64-5717-4562-b3fc-2c963f66afa6/profile",
        headers=staff_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.company_not_found"


async def test_unconfirmed_user_may_edit_the_profile(
    client: AsyncClient, unconfirmed_headers: dict[str, str]
):
    written = await client.put(
        PROFILE,
        json=company_profile_payload(billing_city="Winterthur"),
        headers=unconfirmed_headers,
    )
    read = await client.get(PROFILE, headers=unconfirmed_headers)

    assert written.status_code == 200
    assert read.json()["billing_city"] == "Winterthur"


async def test_unconfirmed_user_may_not_register_a_booking(
    client: AsyncClient,
    unconfirmed_headers: dict[str, str],
    kp_setup,
):
    await client.put(
        PROFILE, json=company_profile_payload(), headers=unconfirmed_headers
    )

    response = await client.post(
        f"/api/kp/events/{kp_setup.event_id}/bookings/register",
        json={"booth_zone_id": kp_setup.booth_zone_id, "confirm_profile": True},
        headers=unconfirmed_headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "error.not_confirmed"
