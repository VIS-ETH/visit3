import { useState } from "react";

export type SortDirection = "asc" | "desc";

export interface SortState<F extends string> {
  field: F;
  direction: SortDirection;
}

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
