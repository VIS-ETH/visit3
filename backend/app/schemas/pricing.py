from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

from app.models.base import PERMILLE_PER_PERCENT, Cents, Permille

VatRatePercent = Annotated[
    Decimal, PlainSerializer(float, return_type=float, when_used="json")
]


class PriceBreakdown(BaseModel):
    net: Cents
    vat: Cents
    gross: Cents


def percent_to_permille(percent: Decimal) -> Permille:
    return int(percent * PERMILLE_PER_PERCENT)
