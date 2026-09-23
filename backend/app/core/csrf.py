from itsdangerous import BadData, URLSafeTimedSerializer

from app.core.config import get_settings

CSRF_COOKIE_KEY = "fastapi-csrf-token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_PATH = "/"
CSRF_TOKEN_MAX_AGE = 3600
CSRF_SIGNATURE_SALT = "fastapi-csrf-token"


def unsign_csrf_token(signed_token: str | None) -> str | None:
    if not signed_token:
        return None

    serializer = URLSafeTimedSerializer(
        get_settings().SECRET_KEY, salt=CSRF_SIGNATURE_SALT
    )
    try:
        token = serializer.loads(signed_token, max_age=CSRF_TOKEN_MAX_AGE)
    except BadData:
        return None

    return token if isinstance(token, str) else None
