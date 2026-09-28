from httpx import AsyncClient, Headers

from app.core.body_limit import DEFAULT_BODY_LIMIT_BYTES


def assert_hardened(headers: Headers) -> None:
    assert headers.get("x-content-type-options") == "nosniff"
    assert "no-store" in headers.get("cache-control", "")


async def test_an_oversized_body_is_refused_with_hardened_headers(
    client: AsyncClient, csrf_headers: dict[str, str]
):
    response = await client.post(
        "/api/auth/register",
        content=b"{" + b" " * (DEFAULT_BODY_LIMIT_BYTES + 1) + b"}",
        headers={**csrf_headers, "Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert_hardened(response.headers)


async def test_the_sso_start_and_callback_are_never_cached(client: AsyncClient):
    initiate = await client.get("/api/auth/initiate")
    callback = await client.get(
        "/api/auth/callback", params={"code": "code", "state": "state"}
    )

    assert "oauth_verifier" in initiate.headers.get("set-cookie", "")
    assert_hardened(initiate.headers)
    assert callback.status_code in {302, 303, 307}
    assert_hardened(callback.headers)


async def test_an_unknown_route_is_hardened_too(client: AsyncClient):
    response = await client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert_hardened(response.headers)
