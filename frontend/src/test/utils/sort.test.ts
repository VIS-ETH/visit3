import { describe, expect, it } from "vitest";
import { sortRows } from "../../utils/sort";

const rows = [
  { name: "Beta", booth: null },
  { name: "Acme", booth: 10 },
  { name: "Zeta", booth: 2 },
  { name: "Gamma", booth: 2 },
];

const order = (direction: "asc" | "desc", field: "name" | "booth") =>
  sortRows(rows, { field, direction }, (row, key) => [row[key], row.name]).map(
    (row) => row.name,
  );

describe("sorting table rows", () => {
  it("sorts numbers numerically and keeps blanks last in both directions", () => {
    expect(order("asc", "booth")).toEqual(["Gamma", "Zeta", "Acme", "Beta"]);
    expect(order("desc", "booth")).toEqual(["Acme", "Zeta", "Gamma", "Beta"]);
  });

  it("sorts text case-insensitively", () => {
    expect(order("desc", "name")).toEqual(["Zeta", "Gamma", "Beta", "Acme"]);
  });

  it("keeps the given order without a sort", () => {
    expect(sortRows(rows, null, () => [])).toBe(rows);
  });
});
