import logging
from typing import Any

import jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)

jwks_client = jwt.PyJWKClient(get_settings().SIP_AUTH_OIDC_JWKS_URL)


def decode_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None

    settings = get_settings()

    try:
        signing_token = jwks_client.get_signing_key_from_jwt(token)
        payload: dict[str, Any] = jwt.decode(
            token,
            signing_token,
            algorithms=[settings.KEYCLOAK_ALGORITHM],
            issuer=settings.SIP_AUTH_OIDC_ISSUER,
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError as e:
        logger.warning("Token decoding failed: %s", e)
        return None
