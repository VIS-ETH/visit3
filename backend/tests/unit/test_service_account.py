import asyncio
import base64
import traceback
from unittest.mock import AsyncMock
from urllib.parse import parse_qs

import grpc
import httpx
import pytest
from authlib.oauth2.rfc6749 import wrappers

from app.core import service_account
from app.core.config import get_oauth_settings
from app.core.grpc import OAuthInterceptor
from app.core.service_account import OAuthTokenError, ServiceAccountCredential

NOW = 2_000_000_000
TOKEN_URL = "https://identity.example.org/oauth/token"


def token_response(token="opaque-access-token", **kwargs):
    return httpx.Response(
        200,
        json={
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 300,
            **kwargs,
        },
    )


@pytest.fixture
def endpoint(monkeypatch):
    requests = []
    responses = [token_response()]
    client_kwargs = []

    async def handle(request):
        requests.append(request)
        await asyncio.sleep(0)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    client_class = service_account.AsyncOAuth2Client

    def client(**kwargs):
        client_kwargs.append(kwargs)
        return client_class(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(service_account, "AsyncOAuth2Client", client)
    monkeypatch.setattr(wrappers.time, "time", lambda: NOW)
    return requests, responses, client_kwargs


@pytest.fixture
async def source(endpoint):
    credential = ServiceAccountCredential(get_oauth_settings())
    try:
        yield credential
    finally:
        await credential.close()


async def test_initial_token_uses_client_credentials_without_scopes(endpoint, source):
    requests, _, client_kwargs = endpoint
    await source.start()
    assert await source.get_access_token() == "opaque-access-token"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == TOKEN_URL
    assert (
        request.headers["authorization"]
        == "Basic "
        + base64.b64encode(b"test-application:test-application-secret").decode()
    )
    assert parse_qs(request.content.decode()) == {"grant_type": ["client_credentials"]}
    assert client_kwargs[0]["verify"] is True
    assert client_kwargs[0]["follow_redirects"] is False


@pytest.mark.parametrize(
    "method",
    [
        b"/sip.notifications.MailService/SendMail",
        b"/sip.notifications.MailService/QueueMail",
    ],
)
async def test_every_rpc_has_bearer_auth_and_preserves_call_options(
    endpoint, source, method
):
    requests, _, _ = endpoint
    await source.start()
    interceptor = OAuthInterceptor(source)
    details = grpc.aio.ClientCallDetails(
        method,
        12,
        grpc.aio.Metadata(("x-request-id", "123"), ("authorization", "stale")),
        None,
        True,
    )
    continuation = AsyncMock()
    request = object()
    for _ in range(2):
        await interceptor.intercept_unary_unary(continuation, details, request)
    assert len(requests) == 1
    for call in continuation.await_args_list:
        actual, sent_request = call.args
        assert sent_request is request
        assert actual.method == method
        assert actual.timeout == 12
        assert actual.wait_for_ready is True
        assert list(actual.metadata) == [
            ("x-request-id", "123"),
            ("authorization", "Bearer opaque-access-token"),
        ]


async def test_library_renews_expired_token_once_for_concurrent_requests(
    endpoint, source, monkeypatch
):
    requests, responses, _ = endpoint
    # Even unsolicited refresh/ID tokens must not change this grant flow.
    responses[:] = [
        token_response(refresh_token="unused-refresh", id_token="unused-id")
    ]
    await source.start()
    monkeypatch.setattr(wrappers.time, "time", lambda: NOW + 301)
    responses.append(token_response("renewed-token"))
    tokens = await asyncio.gather(*(source.get_access_token() for _ in range(10)))
    assert tokens == ["renewed-token"] * 10
    assert len(requests) == 2
    assert parse_qs(requests[1].content.decode()) == {
        "grant_type": ["client_credentials"]
    }
    assert "refresh_token" not in source._client.token
    assert "id_token" not in source._client.token


async def test_library_renews_near_expiry(endpoint, source, monkeypatch):
    requests, responses, _ = endpoint
    await source.start()
    monkeypatch.setattr(wrappers.time, "time", lambda: NOW + 296)
    responses.append(token_response("renewed-token"))
    assert await source.get_access_token() == "renewed-token"
    assert len(requests) == 2


@pytest.mark.parametrize("status", [400, 401])
async def test_detects_body_auth_and_reuses_it_for_renewal(
    endpoint, source, monkeypatch, status
):
    requests, responses, _ = endpoint
    responses[:] = [
        httpx.Response(status, json={"error": "invalid_client"}),
        token_response(),
    ]
    await source.start()
    monkeypatch.setattr(wrappers.time, "time", lambda: NOW + 301)
    responses.append(token_response("renewed-token"))
    assert await source.get_access_token() == "renewed-token"
    assert len(requests) == 3
    for request in requests[1:]:
        assert "authorization" not in request.headers
        assert parse_qs(request.content.decode()) == {
            "grant_type": ["client_credentials"],
            "client_id": ["test-application"],
            "client_secret": ["test-application-secret"],
        }


async def test_renewal_failure_propagates_without_sending_rpc_or_leaking_values(
    endpoint, source, monkeypatch
):
    _, responses, _ = endpoint
    await source.start()
    monkeypatch.setattr(wrappers.time, "time", lambda: NOW + 301)
    responses.append(
        httpx.Response(
            401,
            json={
                "error": "invalid_client",
                "error_description": "test-application-secret opaque-access-token",
            },
        )
    )
    continuation = AsyncMock()
    details = grpc.aio.ClientCallDetails(b"/SendMail", None, None, None, None)
    with pytest.raises(
        OAuthTokenError, match="obtain OAuth access token: HTTP 401"
    ) as error:
        await OAuthInterceptor(source).intercept_unary_unary(
            continuation, details, object()
        )
    continuation.assert_not_awaited()
    formatted = "".join(traceback.format_exception(error.value))
    assert "test-application-secret" not in formatted
    assert "opaque-access-token" not in formatted
    responses.append(token_response("retry-token"))
    assert await source.get_access_token() == "retry-token"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={}),
        httpx.Response(200, json={"access_token": "opaque", "token_type": "Bearer"}),
        token_response(""),
        token_response(token_type="MAC"),
        token_response(expires_in=-10),
        token_response(expires_in="invalid"),
        token_response("bad\nmetadata"),
        httpx.Response(200, text="not json"),
        httpx.Response(500, text="test-application-secret"),
        httpx.ConnectError("TLS failure test-application-secret"),
    ],
)
async def test_token_failures_are_safe_and_propagate(endpoint, source, response):
    _, responses, _ = endpoint
    responses[:] = [response]
    with pytest.raises(OAuthTokenError) as error:
        await source.start()
    assert "test-application-secret" not in "".join(
        traceback.format_exception(error.value)
    )


async def test_redirects_are_not_followed(endpoint, source):
    requests, responses, _ = endpoint
    responses[:] = [
        httpx.Response(302, headers={"location": "http://other.example.org/token"})
    ]
    with pytest.raises(OAuthTokenError, match="HTTP 302"):
        await source.start()
    assert len(requests) == 1


async def test_use_before_start_fails_and_close_releases_http_client(source):
    with pytest.raises(OAuthTokenError, match="not been started"):
        await source.get_access_token()
    await source.close()
    assert source._client.is_closed


@pytest.mark.parametrize(
    "malformed",
    [
        {},
        {"access_token": "bad", "token_type": "Bearer"},
        {"access_token": "bad", "token_type": "MAC", "expires_in": 300},
        {"token_type": "Bearer", "expires_in": 300},
        {
            "access_token": "bad",
            "token_type": "Bearer",
            "expires_in": -1,
            "refresh_token": "unused",
        },
        {"access_token": "bad", "token_type": "Bearer", "expires_in": "invalid"},
    ],
)
async def test_malformed_renewal_does_not_poison_cache_and_next_rpc_recovers(
    endpoint, source, monkeypatch, malformed
):
    requests, responses, _ = endpoint
    await source.start()
    previous_token = source._client.token
    monkeypatch.setattr(wrappers.time, "time", lambda: NOW + 301)
    responses.extend([httpx.Response(200, json=malformed), token_response("recovered")])
    details = grpc.aio.ClientCallDetails(b"/SendMail", None, None, None, None)
    continuation = AsyncMock()
    interceptor = OAuthInterceptor(source)
    with pytest.raises(OAuthTokenError):
        await interceptor.intercept_unary_unary(continuation, details, object())
    continuation.assert_not_awaited()
    assert source._client.token is previous_token

    await interceptor.intercept_unary_unary(continuation, details, object())
    assert list(continuation.await_args.args[0].metadata) == [
        ("authorization", "Bearer recovered")
    ]
    assert len(requests) == 3
    assert parse_qs(requests[-1].content.decode()) == {
        "grant_type": ["client_credentials"]
    }


async def test_short_lived_tokens_are_reused_then_renewed_once(
    endpoint, source, monkeypatch
):
    requests, responses, _ = endpoint
    responses[:] = [token_response(expires_in=30)]
    await source.start()
    assert (
        await asyncio.gather(*(source.get_access_token() for _ in range(5)))
        == ["opaque-access-token"] * 5
    )
    monkeypatch.setattr(wrappers.time, "time", lambda: NOW + 24)
    assert await source.get_access_token() == "opaque-access-token"
    assert len(requests) == 1

    monkeypatch.setattr(wrappers.time, "time", lambda: NOW + 26)
    responses.append(token_response("renewed-short-token", expires_in=30))
    assert (
        await asyncio.gather(*(source.get_access_token() for _ in range(5)))
        == ["renewed-short-token"] * 5
    )
    assert len(requests) == 2
