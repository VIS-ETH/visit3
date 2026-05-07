export function formatPrice(cents: number) {
  return (cents / 100).toFixed(2);
}

export function centsToCurrencyAmount(
  cents: number | null | undefined,
): number {
  if (cents == null || Number.isNaN(cents)) return 0;
  return cents / 100;
}

export function currencyAmountToCents(
  amount: number | null | undefined,
): number {
  if (amount == null || Number.isNaN(amount)) return 0;
  return Math.round(amount * 100);
}
