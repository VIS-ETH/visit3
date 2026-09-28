import logging
import re

REDACTED = "[redacted]"
TOKEN_PATH = re.compile(
    r"(/(?:auth/reset|auth/link|user/confirm-email|company/invite)/)[^/?#]+"
)
TOKEN_QUERY = re.compile(r"([?&](?:code|state|session_state|token)=)[^&#]*")


def redact_path(path: str) -> str:
    without_path_tokens = TOKEN_PATH.sub(rf"\1{REDACTED}", path)
    return TOKEN_QUERY.sub(rf"\1{REDACTED}", without_path_tokens)


class AccessLogRedaction(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) >= 3:
            arguments = list(record.args)
            arguments[2] = redact_path(str(arguments[2]))
            record.args = tuple(arguments)
        return True
