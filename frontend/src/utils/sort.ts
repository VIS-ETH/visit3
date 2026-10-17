import { useState } from "react";

export type SortDirection = "asc" | "desc";

export interface SortState<F extends string> {
  field: F;
  direction: SortDirection;
}

export type SortValue = string | number | null | undefined;

export function useSort<F extends string>(
  initial: SortState<F> | null,
  onChange?: () => void,
) {
  const [sort, setSort] = useState<SortState<F> | null>(initial);
  const toggleSort = (field: F) => {
    onChange?.();
    setSort((current) =>
      current?.field === field
        ? { field, direction: current.direction === "asc" ? "desc" : "asc" }
        : { field, direction: "asc" },
    );
  };
  return { sort, toggleSort };
}

const isBlank = (value: SortValue) =>
  value === null || value === undefined || value === "";

export function sortRows<T, F extends string>(
  rows: T[],
  sort: SortState<F> | null,
  valuesOf: (row: T, field: F) => SortValue[],
): T[] {
  if (!sort) return rows;
  const factor = sort.direction === "asc" ? 1 : -1;
  const compare = (left: SortValue, right: SortValue) => {
    if (isBlank(left) || isBlank(right)) {
      return Number(isBlank(left)) - Number(isBlank(right));
    }
    return (
      factor *
      (typeof left === "number" && typeof right === "number"
        ? left - right
        : String(left).localeCompare(String(right), undefined, {
            numeric: true,
            sensitivity: "base",
          }))
    );
  };
  return [...rows].sort((left, right) => {
    const leftValues = valuesOf(left, sort.field);
    const rightValues = valuesOf(right, sort.field);
    for (const [index, value] of leftValues.entries()) {
      const result = compare(value, rightValues[index]);
      if (result !== 0) return result;
    }
    return 0;
  });
}
