from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.mail_templates.defaults import MAIL_TEMPLATE_DEFAULTS
from app.mail_templates.keys import MailTemplateKey
from app.models.user import User
from tests.api.conftest import decoded_subject

KEY = str(MailTemplateKey.PASSWORD_RESET)
VALID_BODY = {
    "subject_de": "Passwort zurücksetzen",
    "subject_en": "Reset password",
    "body_de": '<p>Hallo {{ name }}: <a href="{{ reset_url }}">Los</a></p>',
    "body_en": '<p>Hello {{ name }}: <a href="{{ reset_url }}">Go</a></p>',
}


@pytest.fixture
async def plain_staff_headers(
    staff_user: User,
    auth_headers: Callable[[User], Awaitable[dict[str, str]]],
    csrf_headers: dict[str, str],
) -> dict[str, str]:
    return {**await auth_headers(staff_user), **csrf_headers}


async def test_listing_covers_every_key_and_defaults_to_code_texts(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.get("/api/mail-templates", headers=plain_staff_headers)

    assert response.status_code == 200
    templates = response.json()
    assert [template["key"] for template in templates] == [
        str(key) for key in MailTemplateKey
    ]
    assert all(template["is_customized"] is False for template in templates)


async def test_company_user_cannot_read_templates(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.get("/api/mail-templates", headers=company_headers)

    assert response.status_code == 403


async def test_single_template_falls_back_to_the_default(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.get(
        f"/api/mail-templates/{KEY}", headers=plain_staff_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert (
        body["body_de"]
        == MAIL_TEMPLATE_DEFAULTS[MailTemplateKey.PASSWORD_RESET].body_de
    )
    assert body["is_customized"] is False
    assert body["variables"] == ["name", "reset_url"]


async def test_default_texts_are_exposed_next_to_the_stored_ones(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    await client.put(
        f"/api/mail-templates/{KEY}", json=VALID_BODY, headers=plain_staff_headers
    )

    response = await client.get(
        f"/api/mail-templates/{KEY}", headers=plain_staff_headers
    )

    body = response.json()
    defaults = MAIL_TEMPLATE_DEFAULTS[MailTemplateKey.PASSWORD_RESET]
    assert body["body_de"] == VALID_BODY["body_de"]
    assert body["default_body_de"] == defaults.body_de
    assert body["default_body_en"] == defaults.body_en
    assert body["default_subject_de"] == defaults.subject_de
    assert body["default_subject_en"] == defaults.subject_en


async def test_defaults_match_the_texts_while_nothing_is_stored(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.get("/api/mail-templates", headers=plain_staff_headers)

    assert all(
        template["default_body_de"] == template["body_de"]
        and template["default_subject_en"] == template["subject_en"]
        for template in response.json()
    )


async def test_unknown_key_is_not_found(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.get(
        "/api/mail-templates/not_a_template", headers=plain_staff_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.mail_template_not_found"


async def test_update_stores_the_template_and_marks_it_customized(
    client: AsyncClient, plain_staff_headers: dict[str, str], staff_user: User
):
    update = await client.put(
        f"/api/mail-templates/{KEY}", json=VALID_BODY, headers=plain_staff_headers
    )

    assert update.status_code == 200
    assert update.json()["is_customized"] is True
    assert update.json()["updated_by_user_id"] == str(staff_user.id)

    stored = await client.get(f"/api/mail-templates/{KEY}", headers=plain_staff_headers)

    assert stored.json()["subject_en"] == "Reset password"


async def test_update_rejects_unknown_variables(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.put(
        f"/api/mail-templates/{KEY}",
        json={**VALID_BODY, "body_en": "<p>{{ nickname }}</p>"},
        headers=plain_staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.mail_template_invalid"
    assert "nickname" in response.json()["message"]
    assert response.json()["details"] == {"field": "body_en", "variable": "nickname"}


async def test_update_rejects_broken_syntax(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.put(
        f"/api/mail-templates/{KEY}",
        json={**VALID_BODY, "body_de": "<p>{% for %}</p>"},
        headers=plain_staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.mail_template_invalid"
    assert response.json()["details"] == {"field": "body_de"}


async def test_update_rejects_a_sandbox_violation(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.put(
        f"/api/mail-templates/{KEY}",
        json={**VALID_BODY, "body_en": "<p>{{ name.__class__ }}</p>"},
        headers=plain_staff_headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "error.mail_template_invalid"
    assert response.json()["details"] == {"field": "body_en"}


async def test_company_user_cannot_update_a_template(
    client: AsyncClient, company_headers: dict[str, str]
):
    response = await client.put(
        f"/api/mail-templates/{KEY}", json=VALID_BODY, headers=company_headers
    )

    assert response.status_code == 403


async def test_reset_removes_the_stored_template_and_restores_the_default(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    await client.put(
        f"/api/mail-templates/{KEY}", json=VALID_BODY, headers=plain_staff_headers
    )

    response = await client.delete(
        f"/api/mail-templates/{KEY}", headers=plain_staff_headers
    )
    stored = await client.get(f"/api/mail-templates/{KEY}", headers=plain_staff_headers)

    defaults = MAIL_TEMPLATE_DEFAULTS[MailTemplateKey.PASSWORD_RESET]
    assert response.status_code == 200
    assert response.json()["is_customized"] is False
    assert response.json()["body_de"] == defaults.body_de
    assert stored.json()["is_customized"] is False
    assert stored.json()["body_de"] == defaults.body_de


async def test_reset_can_be_repeated_when_nothing_is_stored(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.delete(
        f"/api/mail-templates/{KEY}", headers=plain_staff_headers
    )

    assert response.status_code == 200
    assert response.json()["is_customized"] is False


async def test_reset_of_an_unknown_key_is_not_found(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    response = await client.delete(
        "/api/mail-templates/not_a_template", headers=plain_staff_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "error.mail_template_not_found"


async def test_customized_template_survives_a_reset_by_a_company_user(
    client: AsyncClient,
    plain_staff_headers: dict[str, str],
    company_headers: dict[str, str],
):
    await client.put(
        f"/api/mail-templates/{KEY}", json=VALID_BODY, headers=plain_staff_headers
    )

    response = await client.delete(
        f"/api/mail-templates/{KEY}", headers=company_headers
    )
    stored = await client.get(f"/api/mail-templates/{KEY}", headers=plain_staff_headers)

    assert response.status_code == 403
    assert stored.json()["is_customized"] is True


async def test_reset_lets_the_default_text_be_sent_again(
    client: AsyncClient, plain_staff_headers: dict[str, str], mail_stub: AsyncMock
):
    await client.put(
        f"/api/mail-templates/{KEY}",
        json={**VALID_BODY, "subject_de": "Eigener Betreff"},
        headers=plain_staff_headers,
    )
    await client.delete(f"/api/mail-templates/{KEY}", headers=plain_staff_headers)

    await client.post(
        f"/api/mail-templates/{KEY}/test-send", headers=plain_staff_headers
    )

    message = mail_stub.SendMail.await_args.args[0]
    assert decoded_subject(message).startswith("VISIT: Passwort zurücksetzen")


async def test_preview_renders_both_languages_with_sample_values(
    client: AsyncClient, plain_staff_headers: dict[str, str]
):
    await client.put(
        f"/api/mail-templates/{KEY}", json=VALID_BODY, headers=plain_staff_headers
    )

    response = await client.post(
        f"/api/mail-templates/{KEY}/preview", headers=plain_staff_headers
    )

    assert response.status_code == 200
    preview = response.json()
    assert preview["subject"] == "Passwort zurücksetzen / Reset password"
    assert preview["html"].index("Hallo Ada") < preview["html"].index("Hello Ada")
    assert "Los (https://visit.vis.ethz.ch/reset/sample-token)" in preview["text"]


async def test_test_send_mails_the_caller_once(
    client: AsyncClient,
    plain_staff_headers: dict[str, str],
    staff_user: User,
    mail_stub: AsyncMock,
):
    response = await client.post(
        f"/api/mail-templates/{KEY}/test-send", headers=plain_staff_headers
    )

    assert response.status_code == 200
    mail_stub.SendMail.assert_awaited_once()
    message = mail_stub.SendMail.await_args.args[0]
    assert [address.mail_address.address for address in message.to] == [
        staff_user.email
    ]
    assert decoded_subject(message).startswith("VISIT: Passwort zurücksetzen")


async def test_company_user_cannot_trigger_a_test_send(
    client: AsyncClient, company_headers: dict[str, str], mail_stub: AsyncMock
):
    response = await client.post(
        f"/api/mail-templates/{KEY}/test-send", headers=company_headers
    )

    assert response.status_code == 403
    mail_stub.SendMail.assert_not_awaited()
