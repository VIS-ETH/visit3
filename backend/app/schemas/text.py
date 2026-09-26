from typing import Annotated

from pydantic import AfterValidator, BeforeValidator

from app.core.utils import reject_control_characters, strip_text


def _strip(value: object) -> object:
    return strip_text(value) if isinstance(value, str) else value


SingleLineText = Annotated[
    str, BeforeValidator(_strip), AfterValidator(reject_control_characters)
]
