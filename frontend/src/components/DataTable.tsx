import {
  Center,
  Group,
  Loader,
  Pagination,
  Select,
  Table,
  Text,
  TextInput,
  type TableProps,
} from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { type ReactNode, useEffect, useMemo, useState } from "react";

export type DataTableColumn<T> = {
  key: string;
  header: ReactNode;
  render: (item: T) => ReactNode;
  searchableValue?: (item: T) => string;
  textAlign?: "left" | "center" | "right";
  width?: number | string;
};

type DataTableSearchLabels = {
  noResults: string;
  placeholder: string;
};

type DataTablePaginationLabels = {
  pageSummary: (first: number, last: number, total: number) => string;
  rowsPerPage: string;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  data: T[] | undefined;
  emptyLabel: string;
  getRowKey: (item: T) => string;
  isLoading?: boolean;
  minWidth?: number;
  onRowClick?: (item: T) => void;
  pageSizeOptions?: number[];
  pagination?: DataTablePaginationLabels;
  search?: DataTableSearchLabels;
  tableProps?: TableProps;
};

const defaultPageSizeOptions = [10, 25, 50];

export const DataTableEmptyCell = ({ label = "-" }: { label?: ReactNode }) => (
  <Text c="dimmed" size="sm">
    {label}
  </Text>
);

const DataTable = <T,>({
  columns,
  data,
  emptyLabel,
  getRowKey,
  isLoading = false,
  minWidth = 700,
  onRowClick,
  pageSizeOptions = defaultPageSizeOptions,
  pagination,
  search: searchConfig,
  tableProps,
}: DataTableProps<T>) => {
  const rows = useMemo(() => data ?? [], [data]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(pageSizeOptions[0] ?? 10);

  const normalizedSearch = searchConfig ? search.trim().toLowerCase() : "";
  const filteredRows = useMemo(() => {
    if (!normalizedSearch) return rows;

    return rows.filter((row) =>
      columns.some((column) =>
        column.searchableValue?.(row).toLowerCase().includes(normalizedSearch),
      ),
    );
  }, [columns, normalizedSearch, rows]);

  const shouldPaginate = Boolean(pagination);
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const firstItemIndex =
    filteredRows.length === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastItemIndex = Math.min(page * pageSize, filteredRows.length);
  const visibleRows = shouldPaginate
    ? filteredRows.slice((page - 1) * pageSize, page * pageSize)
    : filteredRows;
  const hasRows = rows.length > 0;
  const hasFilteredRows = filteredRows.length > 0;

  useEffect(() => {
    setPage(1);
  }, [normalizedSearch, pageSize]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  if (isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  return (
    <>
      {hasRows && (searchConfig || pagination) ? (
        <Group align="flex-end" gap="sm" justify="space-between" mb="sm">
          {searchConfig ? (
            <TextInput
              flex={1}
              leftSection={<IconSearch size={16} />}
              maw={360}
              onChange={(event) => setSearch(event.currentTarget.value)}
              placeholder={searchConfig.placeholder}
              value={search}
            />
          ) : (
            <div />
          )}
          {pagination && hasFilteredRows ? (
            <Group gap="xs" align="center">
              <Text c="dimmed" size="sm">
                {pagination.rowsPerPage}
              </Text>
              <Select
                allowDeselect={false}
                aria-label={pagination.rowsPerPage}
                data={pageSizeOptions.map((option) => String(option))}
                onChange={(value) => setPageSize(Number(value ?? pageSize))}
                value={String(pageSize)}
                w={96}
              />
            </Group>
          ) : null}
        </Group>
      ) : null}

      {!hasRows ? (
        <Text c="dimmed">{emptyLabel}</Text>
      ) : !hasFilteredRows ? (
        <Text c="dimmed">{searchConfig?.noResults ?? emptyLabel}</Text>
      ) : (
        <>
          <Table.ScrollContainer minWidth={minWidth}>
            <Table highlightOnHover {...tableProps}>
              <Table.Thead>
                <Table.Tr>
                  {columns.map((column) => (
                    <Table.Th
                      key={column.key}
                      ta={column.textAlign}
                      w={column.width}
                    >
                      {column.header}
                    </Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {visibleRows.map((row) => (
                  <Table.Tr
                    key={getRowKey(row)}
                    role={onRowClick ? "button" : undefined}
                    tabIndex={onRowClick ? 0 : undefined}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    onKeyDown={
                      onRowClick
                        ? (event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              onRowClick(row);
                            }
                          }
                        : undefined
                    }
                    style={onRowClick ? { cursor: "pointer" } : undefined}
                  >
                    {columns.map((column) => (
                      <Table.Td key={column.key} ta={column.textAlign}>
                        {column.render(row)}
                      </Table.Td>
                    ))}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>

          {pagination ? (
            <Group justify="space-between" mt="sm">
              <Text c="dimmed" size="sm">
                {pagination.pageSummary(
                  firstItemIndex,
                  lastItemIndex,
                  filteredRows.length,
                )}
              </Text>
              <Pagination
                onChange={setPage}
                total={totalPages}
                value={page}
                withEdges
              />
            </Group>
          ) : null}
        </>
      )}
    </>
  );
};

export default DataTable;
