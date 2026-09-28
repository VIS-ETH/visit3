from collections.abc import Callable

from app.core.cookies import secure_cookies
from app.main import CsrfSettings


def test_cookies_stay_plain_in_debug(debug_setting: Callable[[bool], None]):
    debug_setting(True)

    assert secure_cookies() is False
    assert CsrfSettings().cookie_secure is False


def test_cookies_require_https_outside_debug(debug_setting: Callable[[bool], None]):
    debug_setting(False)

    assert secure_cookies() is True
    assert CsrfSettings().cookie_secure is True
