from app.core.config import get_settings


def secure_cookies() -> bool:
    return not get_settings().DEBUG
