from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field

from app.core.utils import reject_control_characters, strip_text

NAME_MAX_LENGTH = 100
COMPANY_NAME_MAX_LENGTH = 200
PHONE_MAX_LENGTH = 50
REQUIREMENT_TEXT_MAX_LENGTH = 5000
PROFILE_TEXT_LIMITS = {
    "brand_name": COMPANY_NAME_MAX_LENGTH,
    "website": 2048,
    "general_phone": PHONE_MAX_LENGTH,
    "places_of_work": 500,
    "billing_company_name": COMPANY_NAME_MAX_LENGTH,
    "billing_street": 200,
    "billing_house_number": 20,
    "billing_postal_code": 20,
    "billing_city": 100,
    "billing_vat_number": 50,
}


def _strip(value: object) -> object:
    return strip_text(value) if isinstance(value, str) else value


CompanyName = Annotated[
    str,
    Field(max_length=COMPANY_NAME_MAX_LENGTH),
    BeforeValidator(_strip),
    AfterValidator(reject_control_characters),
]
PersonName = Annotated[
    str,
    Field(min_length=1, max_length=NAME_MAX_LENGTH),
    BeforeValidator(_strip),
    AfterValidator(reject_control_characters),
]
