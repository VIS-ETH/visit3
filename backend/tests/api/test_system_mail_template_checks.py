from httpx import AsyncClient

URL = "/api/mail-templates/password_reset"


async def test_a_reset_template_without_the_reset_link_is_rejected(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.put(
        URL,
        json={
            "subject_de": "Passwort",
            "subject_en": "Password",
            "body_de": "<p>Hallo {{ name }} {{ reset_url }}</p>",
            "body_en": "<p>Hello {{ name }}</p>",
        },
        headers=staff_headers,
    )

    assert response.status_code == 400, response.text
    assert response.json()["code"] == "error.mail_template_invalid"


async def test_a_template_failing_while_rendering_is_rejected(
    client: AsyncClient, staff_headers: dict[str, str]
):
    response = await client.put(
        URL,
        json={
            "subject_de": "s",
            "subject_en": "s",
            "body_de": "{{ reset_url < 1 }}",
            "body_en": "{{ reset_url }}",
        },
        headers=staff_headers,
    )

    assert response.status_code == 400, response.text
    assert response.json()["code"] == "error.mail_template_invalid"
