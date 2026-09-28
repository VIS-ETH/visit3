from decimal import ROUND_HALF_EVEN, Decimal

from app.models.base import Cents, Permille
from app.schemas.pricing import PriceBreakdown

PERMILLE = Decimal(1000)
WHOLE_CENT = Decimal(1)


def price_breakdown(net_cents: Cents, vat_rate_permille: Permille) -> PriceBreakdown:
    vat_cents = int(
        (Decimal(net_cents) * Decimal(vat_rate_permille) / PERMILLE).quantize(
            WHOLE_CENT, rounding=ROUND_HALF_EVEN
        )
    )
    return PriceBreakdown(net=net_cents, vat=vat_cents, gross=net_cents + vat_cents)
