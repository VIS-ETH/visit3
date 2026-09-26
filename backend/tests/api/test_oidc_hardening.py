import base64
import hashlib
from typing import Any
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient

from app.core import security
from app.core.config import get_settings
from app.core.exceptions import KeycloakExchangeFailed
from app.services.auth_service import AuthService

LOGIN_ERROR = f"{get_settings().VISIT_FRONTEND_SERVER_URL}/login?error=server.error"


def challenge_of(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


async def test_the_login_url_carries_a_pkce_challenge(client: AsyncClient):
    response = await client.get("/api/auth/initiate")

    query = parse_qs(urlsplit(response.json()).query)
    verifier = response.cookies["oauth_verifier"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [challenge_of(verifier)]
    assert query["state"] == [response.cookies["oauth_state"]]
    assert query["redirect_uri"] == [get_settings().KEYCLOAK_CALLBACK]
    assert len(verifier) >= 43
    assert "HttpOnly" in response.headers.get_list("set-cookie")[-1]


async def test_the_callback_sends_the_code_verifier(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    exchanges: list[tuple[str, str]] = []

    async def exchange(_service: AuthService, code: str, verifier: str) -> str:
        exchanges.append((code, verifier))
        return "issued-refresh-token"

    monkeypatch.setattr(AuthService, "keycloak_callback", exchange)
    client.cookies.set("oauth_state", "matching-state")
    client.cookies.set("oauth_verifier", "the-verifier")

    response = await client.get(
        "/api/auth/callback?code=auth-code&state=matching-state"
    )

    assert exchanges == [("auth-code", "the-verifier")]
    assert "oauth_verifier" in response.headers.get("set-cookie", "")


async def test_the_callback_refuses_a_login_without_a_verifier(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def exchange(*_args: object) -> str:
        raise AssertionError("the exchange must not run without a verifier")

    monkeypatch.setattr(AuthService, "keycloak_callback", exchange)
    client.cookies.set("oauth_state", "matching-state")

    response = await client.get(
        "/api/auth/callback?code=auth-code&state=matching-state"
    )

    assert response.headers["location"] == LOGIN_ERROR


async def test_the_token_exchange_includes_the_verifier(
    auth_service: AuthService, monkeypatch: pytest.MonkeyPatch
):
    payloads: list[dict[str, str]] = []

    async def token_endpoint(payload: dict[str, str]) -> Any:
        payloads.append(payload)
        raise KeycloakExchangeFailed("stop")

    monkeypatch.setattr(auth_service, "_token_endpoint", token_endpoint)

    with pytest.raises(KeycloakExchangeFailed):
        await auth_service.keycloak_callback("auth-code", "the-verifier")

    assert payloads[0]["code_verifier"] == "the-verifier"


async def test_a_token_without_email_claim_is_refused_cleanly(
    auth_service: AuthService,
):
    claims = {
        "sub": "no-email",
        "resource_access": {
            get_settings().SIP_AUTH_OIDC_CLIENT_ID: {"roles": ["vis-active"]}
        },
    }

    with pytest.raises(KeycloakExchangeFailed):
        await auth_service.map_keycloak_to_user(claims)


@pytest.fixture
def signing_key(monkeypatch: pytest.MonkeyPatch) -> rsa.RSAPrivateKey:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        security.jwks_client,
        "get_signing_key_from_jwt",
        lambda _token: key.public_key(),
    )
    return key


def keycloak_token(key: rsa.RSAPrivateKey, **claims: Any) -> str:
    payload = {"iss": get_settings().SIP_AUTH_OIDC_ISSUER, "sub": "user", **claims}
    return jwt.encode(payload, key, algorithm=get_settings().KEYCLOAK_ALGORITHM)


@pytest.mark.parametrize(
    "claims",
    [
        {"azp": get_settings().SIP_AUTH_OIDC_CLIENT_ID, "aud": "account"},
        {
            "azp": "other-client",
            "aud": ["account", get_settings().SIP_AUTH_OIDC_CLIENT_ID],
        },
        {"aud": get_settings().SIP_AUTH_OIDC_CLIENT_ID},
    ],
)
def test_a_token_for_this_client_is_accepted(
    signing_key: rsa.RSAPrivateKey, claims: dict[str, Any]
):
    assert security.decode_token(keycloak_token(signing_key, **claims)) is not None


@pytest.mark.parametrize(
    "claims",
    [{"azp": "other-client", "aud": "other-client"}, {"aud": "account"}, {}],
)
def test_a_token_for_another_client_is_refused(
    signing_key: rsa.RSAPrivateKey, claims: dict[str, Any]
):
    assert security.decode_token(keycloak_token(signing_key, **claims)) is None
