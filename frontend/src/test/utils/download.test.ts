import { describe, expect, it } from "vitest";
import { safeFilenamePart } from "../../utils/download";

describe("safeFilenamePart", () => {
  it("drops accents and joins words with dashes", () => {
    expect(safeFilenamePart(" Kontaktparty Zürich 2026 ")).toBe(
      "kontaktparty-zurich-2026",
    );
  });

  it("keeps non-latin names recognisable", () => {
    expect(safeFilenamePart("北京大学")).toBe("北京大学");
  });

  it("falls back to a generic name without letters or digits", () => {
    expect(safeFilenamePart("?!")).toBe("download");
  });
});
