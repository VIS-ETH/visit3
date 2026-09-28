from typing import Any, cast

import httpx
from authlib.integrations.base_client import OAuthError
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749 import OAuth2Token

from app.core.config import OAuthSettings

TOKEN_RENEWAL_MARGIN_SECONDS = 5


class OAuthTokenError(RuntimeError):
    """A safe error to propagate without exposing token endpoint response bodies."""


class ServiceAccountCredential:
    """Lifecycle-owned OAuth client; Authlib owns token caching and renewal."""

    def __init__(self, settings: OAuthSettings):
        # Authlib's client is untyped; keep that boundary inside this adapter.
        self._client = cast(Any, AsyncOAuth2Client)(
            client_id=settings.SIP_AUTH_OIDC_CLIENT_ID,
            client_secret=settings.SIP_AUTH_OIDC_CLIENT_SECRET.get_secret_value(),
            token_endpoint=str(settings.SIP_AUTH_OIDC_TOKEN_ENDPOINT),
            grant_type="client_credentials",
            leeway=TOKEN_RENEWAL_MARGIN_SECONDS,
            timeout=10,
            verify=True,
            follow_redirects=False,
        )
        self._client.register_compliance_hook(
            "access_token_response", self._check_response
        )

    @staticmethod
    def _check_response(response: httpx.Response) -> httpx.Response:
        if (
            response.status_code == 400
            and response.json().get("error") == "invalid_client"
        ):
            raise OAuthError(error="invalid_client")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise OAuthTokenError("OAuth token endpoint returned an invalid response")
        if "error" in payload:
            # Preserve Authlib's OAuth error handling, including auth detection.
            return response
        # Normalize and validate before Authlib replaces its cached token.
        # A rejected renewal leaves the old expired token available for retry.
        token = cast(Any, OAuth2Token)(payload)
        ServiceAccountCredential._validate_token(token)
        # Client credentials must renew with that grant, even when a provider
        # returns unsolicited refresh or ID tokens.
        token.pop("refresh_token", None)
        token.pop("id_token", None)
        return httpx.Response(
            response.status_code, json=token, request=response.request
        )

    async def start(self) -> None:
        try:
            try:
                await self._client.fetch_token()
            except (OAuthError, httpx.HTTPStatusError) as error:
                # Authlib defaults to Basic. Probe body authentication only if
                # the server rejects client authentication, then reuse it.
                rejected_client = (
                    isinstance(error, OAuthError) and error.error == "invalid_client"
                ) or (
                    isinstance(error, httpx.HTTPStatusError)
                    and error.response.status_code == 401
                )
                if not rejected_client:
                    raise
                self._client.token_endpoint_auth_method = "client_secret_post"
                await self._client.fetch_token()
        except Exception as error:
            raise self._safe_error(error) from None

    async def get_access_token(self) -> str:
        try:
            if not self._client.token:
                raise OAuthTokenError("OAuth token source has not been started")
            await self._client.ensure_active_token(self._client.token)
            return self._validate_token(self._client.token)
        except Exception as error:
            raise self._safe_error(error) from None

    @staticmethod
    def _validate_token(token: Any) -> str:
        access_token = token.get("access_token")
        # OAuth tokens can be opaque. Expiry comes from the OAuth response,
        # never from unverified JWT claims. Require it so renewal is reliable.
        if (
            not isinstance(access_token, str)
            or not access_token
            or any(ord(char) < 33 or ord(char) > 126 for char in access_token)
            or str(token.get("token_type", "")).lower() != "bearer"
            or not isinstance(token.get("expires_at"), int)
            or token.is_expired(leeway=0)
        ):
            raise OAuthTokenError(
                "OAuth token endpoint returned an invalid bearer token or expiry"
            )
        return access_token

    @staticmethod
    def _safe_error(error: Exception) -> OAuthTokenError:
        if isinstance(error, OAuthTokenError):
            return error
        if isinstance(error, httpx.HTTPStatusError):
            reason = f"HTTP {error.response.status_code}"
        elif isinstance(error, OAuthError):
            reason = "authorization server rejected the client-credentials request"
        elif isinstance(error, httpx.RequestError):
            reason = "token endpoint connection, TLS, or timeout failure"
        else:
            reason = "invalid token endpoint response"
        # Never include remote descriptions, response bodies, URLs, or tokens.
        return OAuthTokenError(f"obtain OAuth access token: {reason}")

    async def close(self) -> None:
        await self._client.aclose()
