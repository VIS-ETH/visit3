import type { PriceBreakdown } from "../orval/generated/fastAPI.schemas";

const PERMILLE = 1000;
const PERMILLE_PER_PERCENT = 10;

const divideHalfEven = (numerator: number, denominator: number) => {
  const sign = numerator < 0 ? -1 : 1;
  const dividend = Math.abs(numerator);
  const quotient = Math.floor(dividend / denominator);
  const doubledRemainder = (dividend % denominator) * 2;
  if (doubledRemainder > denominator) return sign * (quotient + 1);
  if (doubledRemainder < denominator) return sign * quotient;
  return sign * (quotient % 2 === 0 ? quotient : quotient + 1);
};

export const vatRatePermille = (vatRatePercent: number) =>
  Math.round(vatRatePercent * PERMILLE_PER_PERCENT);

export const vatCents = (netCents: number, vatRatePercent: number) =>
  divideHalfEven(netCents * vatRatePermille(vatRatePercent), PERMILLE);

export const priceBreakdown = (
  netCents: number,
  vatRatePercent: number,
): PriceBreakdown => {
  const vat = vatCents(netCents, vatRatePercent);
  return { net: netCents, vat, gross: netCents + vat };
};
