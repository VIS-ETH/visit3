import { describe, expect, it } from "vitest";
import { priceBreakdown, vatCents, vatRatePermille } from "../../utils/pricing";

describe("vatRatePermille", () => {
  it("converts a fractional percent rate to whole permille", () => {
    expect(vatRatePermille(8.1)).toBe(81);
    expect(vatRatePermille(7.7)).toBe(77);
    expect(vatRatePermille(0)).toBe(0);
    expect(vatRatePermille(20)).toBe(200);
  });
});

describe("vatCents", () => {
  it("applies the rate to the net amount", () => {
    expect(vatCents(100000, 8.1)).toBe(8100);
    expect(vatCents(0, 8.1)).toBe(0);
    expect(vatCents(105000, 8.1)).toBe(8505);
  });

  it("rounds a half cent to the even neighbour", () => {
    expect(vatCents(500, 1)).toBe(5);
    expect(vatCents(5, 50)).toBe(2);
    expect(vatCents(15, 50)).toBe(8);
    expect(vatCents(25, 50)).toBe(12);
    expect(vatCents(35, 50)).toBe(18);
  });

  it("rounds a remainder below and above the half cent to its neighbour", () => {
    expect(vatCents(100, 8.1)).toBe(8);
    expect(vatCents(100, 8.9)).toBe(9);
  });

  it("keeps the sign of a negative net amount", () => {
    expect(vatCents(-100000, 8.1)).toBe(-8100);
    expect(vatCents(-5, 50)).toBe(-2);
  });
});

describe("priceBreakdown", () => {
  it("adds the vat to the net amount", () => {
    expect(priceBreakdown(60000, 8.1)).toEqual({
      net: 60000,
      vat: 4860,
      gross: 64860,
    });
  });

  it("leaves the gross equal to the net without vat", () => {
    expect(priceBreakdown(60000, 0)).toEqual({
      net: 60000,
      vat: 0,
      gross: 60000,
    });
  });
});
