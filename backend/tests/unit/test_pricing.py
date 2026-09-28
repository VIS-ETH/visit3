from decimal import Decimal

import pytest

from app.schemas.pricing import percent_to_permille
from app.services.pricing import price_breakdown


@pytest.mark.parametrize(
    ("net_cents", "vat_rate_permille", "expected_vat"),
    [
        (10000, 0, 0),
        (10000, 81, 810),
        (10000, 77, 770),
        (10000, 26, 260),
        (1, 81, 0),
        (7, 81, 1),
        (123456789, 81, 10000000),
    ],
)
def test_vat_is_the_net_amount_times_the_rate(
    net_cents: int, vat_rate_permille: int, expected_vat: int
):
    breakdown = price_breakdown(net_cents, vat_rate_permille)

    assert breakdown.net == net_cents
    assert breakdown.vat == expected_vat
    assert breakdown.gross == net_cents + expected_vat


@pytest.mark.parametrize(
    ("net_cents", "expected_vat"),
    [(500, 40), (1500, 122), (2500, 202), (3500, 284)],
)
def test_half_cents_round_to_the_nearest_even_cent(net_cents: int, expected_vat: int):
    assert price_breakdown(net_cents, 81).vat == expected_vat


def test_gross_is_not_rounded_to_five_rappen():
    breakdown = price_breakdown(100, 81)

    assert (breakdown.vat, breakdown.gross) == (8, 108)


def test_zero_net_stays_zero():
    assert price_breakdown(0, 81) == price_breakdown(0, 0)


@pytest.mark.parametrize(
    ("percent", "expected_permille"),
    [("0", 0), ("2.6", 26), ("7.7", 77), ("8.1", 81), ("100", 1000)],
)
def test_percent_converts_to_permille_without_loss(
    percent: str, expected_permille: int
):
    assert percent_to_permille(Decimal(percent)) == expected_permille
