import jwt

from app.core.config import get_settings

jwks_client = jwt.PyJWKClient(get_settings().SIP_AUTH_OIDC_JWKS_URL)


def decode_token(token: str):
    signing_token = jwks_client.get_signing_key_from_jwt(token)
    settings = get_settings()

    try:
        payload = jwt.decode(
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
        print(f"Decoding failed: {e}")
        return None
