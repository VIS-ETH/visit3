from unittest.mock import MagicMock, patch

import jwt

from app.core import security
from app.core.security import decode_token


def test_decode_token_returns_none_for_missing_token():
    assert decode_token(None) is None
    assert decode_token("") is None


@patch.object(security, "jwks_client")
@patch.object(security, "get_settings")
def test_decode_token_returns_payload_on_success(mock_get_settings, mock_jwks_client):
    settings = MagicMock()
    settings.KEYCLOAK_ALGORITHM = "RS256"
    settings.SIP_AUTH_OIDC_ISSUER = "https://issuer"
    mock_get_settings.return_value = settings

    signing_key = MagicMock()
    mock_jwks_client.get_signing_key_from_jwt.return_value = signing_key

    expected_payload = {"sub": "user-id", "email": "user@example.com"}
    with patch.object(jwt, "decode", return_value=expected_payload) as mock_decode:
        result = decode_token("valid-token")

    assert result == expected_payload
    mock_jwks_client.get_signing_key_from_jwt.assert_called_once_with("valid-token")
    mock_decode.assert_called_once_with(
        "valid-token",
        signing_key,
        algorithms=["RS256"],
        issuer="https://issuer",
        options={"verify_aud": False},
    )


@patch.object(security, "jwks_client")
@patch.object(security, "get_settings")
def test_decode_token_returns_none_on_expired_signature(
    mock_get_settings, mock_jwks_client
):
    mock_get_settings.return_value = MagicMock(KEYCLOAK_ALGORITHM="RS256")
    mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt.ExpiredSignatureError

    assert decode_token("expired-token") is None


@patch.object(security, "jwks_client")
@patch.object(security, "get_settings")
def test_decode_token_returns_none_on_pyjwt_error(mock_get_settings, mock_jwks_client):
    mock_get_settings.return_value = MagicMock(KEYCLOAK_ALGORITHM="RS256")
    mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt.PyJWTError("bad")

    assert decode_token("bad-token") is None
