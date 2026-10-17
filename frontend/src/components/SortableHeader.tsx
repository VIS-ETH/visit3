import { Group, Table, Text, UnstyledButton } from "@mantine/core";
import {
  IconChevronDown,
  IconChevronUp,
  IconSelector,
} from "@tabler/icons-react";
import type { ReactNode } from "react";
import type { SortState } from "../utils/sort";

interface SortableHeaderProps<F extends string> {
  field: F;
  label: ReactNode;
  sort: SortState<F> | null;
  onSort: (field: F) => void;
}

const SortableHeader = <F extends string>({
  field,
  label,
  sort,
  onSort,
}: SortableHeaderProps<F>) => {
  const direction = sort?.field === field ? sort.direction : null;
  return (
    <Table.Th
      aria-sort={
        direction === null
          ? undefined
          : direction === "asc"
            ? "ascending"
            : "descending"
      }
    >
      <UnstyledButton onClick={() => onSort(field)}>
        <Group gap={4} wrap="nowrap">
          <Text fw={600} size="sm">
            {label}
          </Text>
          {direction === null ? (
            <IconSelector size={14} />
          ) : direction === "asc" ? (
            <IconChevronUp size={14} />
          ) : (
            <IconChevronDown size={14} />
          )}
        </Group>
      </UnstyledButton>
    </Table.Th>
  );
};
export default SortableHeader;
