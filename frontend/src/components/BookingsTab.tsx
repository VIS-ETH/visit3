import {
  Anchor,
  Button,
  Center,
  Checkbox,
  Group,
  Loader,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from "@mantine/core";
import {
  IconChevronDown,
  IconChevronUp,
  IconDownload,
  IconSearch,
  IconSelector,
} from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useNavigate } from "react-router";
import { KpBookingStatusBadge } from "./KpBookingStatusBadge";
import BookingNewAdditionsBadge from "./bookings/BookingNewAdditionsBadge";
import BookingCompletenessIcon from "./bookings/BookingCompletenessIcon";
import BookingConfirmModal from "./bookings/BookingConfirmModal";
import BookingDeleteModal from "./bookings/BookingDeleteModal";
import BookingRejectModal from "./bookings/BookingRejectModal";
import BookingRowActions, {
  type BookingRowActionKind,
} from "./bookings/BookingRowActions";
import BoothNumberCell from "./bookings/BoothNumberCell";
import { formatBookingTimestamp } from "./bookings/booking-format";
import { useBookingActions } from "./bookings/useBookingActions";
import {
  downloadEventBookingsCsv,
  type ListEventBookingsQueryResult,
  useListEventBookings,
} from "../orval/generated/kp/kp";
import {
  BOOKING_STATUS_ORDER,
  bookingStatusRank,
  hasNewAdditions,
  canAcceptBooking,
  deleteRequiresForce,
} from "../utils/booking-status";
import { downloadBlob } from "../utils/download";
import { BOOKING_STATUS_LABEL_KEYS } from "../utils/kp-utils";
import { formatPrice } from "../utils/price-utils";

type BookingRow = ListEventBookingsQueryResult[number];
type SortField = "company" | "zone" | "status";
type SortDirection = "asc" | "desc";

const ALL_STATUSES = "ALL";
const PAGE_SIZE = 25;

const SortableHeader = ({
  direction,
  isActive,
  label,
  onSort,
}: {
  direction: SortDirection;
  isActive: boolean;
  label: string;
  onSort: () => void;
}) => (
  <UnstyledButton onClick={onSort}>
    <Group gap={4} wrap="nowrap">
      <Text fw={600} size="sm">
        {label}
      </Text>
      {!isActive ? (
        <IconSelector size={14} />
      ) : direction === "asc" ? (
        <IconChevronUp size={14} />
      ) : (
        <IconChevronDown size={14} />
      )}
    </Group>
  </UnstyledButton>
);

const BookingsTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: bookings, isLoading } = useListEventBookings(eventId);
  const actions = useBookingActions(eventId);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>(ALL_STATUSES);
  const [incompleteOnly, setIncompleteOnly] = useState(false);
  const [sortField, setSortField] = useState<SortField>("company");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeAction, setActiveAction] = useState<{
    booking: BookingRow;
    kind: Exclude<BookingRowActionKind, "open">;
  } | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [page, setPage] = useState(1);

  const rows = useMemo(() => bookings ?? [], [bookings]);
  const visibleRows = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    const filtered = rows.filter((booking) => {
      if (
        normalizedSearch &&
        !booking.company.name.toLowerCase().includes(normalizedSearch)
      ) {
        return false;
      }
      if (statusFilter !== ALL_STATUSES && booking.status !== statusFilter) {
        return false;
      }
      if (incompleteOnly && booking.is_complete !== false) return false;
      return true;
    });

    const factor = sortDirection === "asc" ? 1 : -1;
    return [...filtered].sort((left, right) => {
      if (sortField === "status") {
        return (
          factor *
          (bookingStatusRank(left.status) - bookingStatusRank(right.status))
        );
      }
      const leftValue =
        sortField === "company" ? left.company.name : left.booth_zone.name;
      const rightValue =
        sortField === "company" ? right.company.name : right.booth_zone.name;
      return factor * leftValue.localeCompare(rightValue);
    });
  }, [incompleteOnly, rows, search, sortDirection, sortField, statusFilter]);

  const pageCount = Math.max(1, Math.ceil(visibleRows.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageRows = visibleRows.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );

  const selectableIds = pageRows.map((booking) => booking.id);
  const selectedVisibleIds = selectableIds.filter((id) =>
    selectedIds.includes(id),
  );
  const acceptableSelectedIds = visibleRows
    .filter(
      (booking) =>
        selectedIds.includes(booking.id) && canAcceptBooking(booking.status),
    )
    .map((booking) => booking.id);

  const toggleSort = (field: SortField) => {
    setPage(1);
    if (field === sortField) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
      return;
    }
    setSortField(field);
    setSortDirection("asc");
  };

  const toggleSelection = (bookingId: string, checked: boolean) =>
    setSelectedIds((previous) =>
      checked
        ? [...previous, bookingId]
        : previous.filter((id) => id !== bookingId),
    );

  const toggleAllSelection = (checked: boolean) =>
    setSelectedIds(checked ? selectableIds : []);

  const handleRowAction = (
    action: BookingRowActionKind,
    booking: BookingRow,
  ) => {
    if (action === "open") {
      void navigate(`/kp/${eventId}/bookings/${booking.id}`);
      return;
    }
    setActiveAction({ booking, kind: action });
  };

  const runAction = async (run: () => Promise<void>) => {
    try {
      await run();
    } catch {
      return;
    }
    setActiveAction(null);
  };

  const handleAcceptSelected = async () => {
    try {
      await actions.acceptBookings(acceptableSelectedIds);
    } catch {
      return;
    }
    setSelectedIds([]);
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const content = await downloadEventBookingsCsv(eventId, {
        responseType: "blob",
      });
      downloadBlob(content, "bookings.csv");
    } finally {
      setIsExporting(false);
    }
  };

  const activeBooking = activeAction?.booking;

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="sm">
        <Group justify="space-between" align="flex-end">
          <Title order={4}>{t("kp.manage.bookings_title")}</Title>
          <Group gap="sm">
            <Button
              disabled={acceptableSelectedIds.length === 0}
              loading={actions.isAccepting}
              onClick={() => {
                void handleAcceptSelected();
              }}
            >
              {t("kp.manage.bookings_accept_selected", {
                amount: acceptableSelectedIds.length,
              })}
            </Button>
            <Button
              leftSection={<IconDownload size={16} />}
              loading={isExporting}
              onClick={() => {
                void handleExport();
              }}
              variant="default"
            >
              {t("kp.manage.bookings_export_csv")}
            </Button>
          </Group>
        </Group>

        <Group align="flex-end" gap="sm">
          <TextInput
            flex={1}
            leftSection={<IconSearch size={16} />}
            maw={320}
            onChange={(event) => {
              setPage(1);
              setSearch(event.currentTarget.value);
            }}
            placeholder={t("kp.manage.bookings_search_placeholder")}
            value={search}
          />
          <Select
            allowDeselect={false}
            data={[
              {
                value: ALL_STATUSES,
                label: t("kp.manage.bookings_filter_status_all"),
              },
              ...BOOKING_STATUS_ORDER.map((status) => ({
                value: status,
                label: t(BOOKING_STATUS_LABEL_KEYS[status]),
              })),
            ]}
            label={t("kp.manage.bookings_filter_status")}
            onChange={(value) => {
              setPage(1);
              setStatusFilter(value ?? ALL_STATUSES);
            }}
            value={statusFilter}
            w={200}
          />
          <Checkbox
            checked={incompleteOnly}
            label={t("kp.manage.bookings_filter_incomplete")}
            onChange={(event) => {
              setPage(1);
              setIncompleteOnly(event.currentTarget.checked);
            }}
            pb={8}
          />
        </Group>

        {isLoading ? (
          <Center py="md">
            <Loader />
          </Center>
        ) : rows.length === 0 ? (
          <Text c="dimmed">{t("kp.manage.bookings_empty")}</Text>
        ) : visibleRows.length === 0 ? (
          <Text c="dimmed">{t("kp.manage.bookings_no_results")}</Text>
        ) : (
          <Table.ScrollContainer minWidth={980}>
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th w={40}>
                    <Checkbox
                      aria-label={t("kp.manage.bookings_select_all")}
                      checked={
                        selectedVisibleIds.length === selectableIds.length
                      }
                      indeterminate={
                        selectedVisibleIds.length > 0 &&
                        selectedVisibleIds.length < selectableIds.length
                      }
                      onChange={(event) =>
                        toggleAllSelection(event.currentTarget.checked)
                      }
                    />
                  </Table.Th>
                  <Table.Th>
                    <SortableHeader
                      direction={sortDirection}
                      isActive={sortField === "company"}
                      label={t("kp.manage.booking_company")}
                      onSort={() => toggleSort("company")}
                    />
                  </Table.Th>
                  <Table.Th>
                    <SortableHeader
                      direction={sortDirection}
                      isActive={sortField === "zone"}
                      label={t("kp.manage.booking_booth_zone")}
                      onSort={() => toggleSort("zone")}
                    />
                  </Table.Th>
                  <Table.Th w={110}>{t("kp.manage.booking_booth_nr")}</Table.Th>
                  <Table.Th>
                    <SortableHeader
                      direction={sortDirection}
                      isActive={sortField === "status"}
                      label={t("kp.manage.booking_status")}
                      onSort={() => toggleSort("status")}
                    />
                  </Table.Th>
                  <Table.Th w={110}>
                    {t("kp.manage.booking_completeness")}
                  </Table.Th>
                  <Table.Th w={90}>{t("kp.manage.booking_waitlist")}</Table.Th>
                  <Table.Th>{t("kp.manage.booking_gross_total")}</Table.Th>
                  <Table.Th>
                    {t("kp.manage.booking_status_changed_at")}
                  </Table.Th>
                  <Table.Th w={60}>{t("kp.manage.booking_actions")}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {pageRows.map((booking) => (
                  <Table.Tr key={booking.id}>
                    <Table.Td>
                      <Checkbox
                        aria-label={t("kp.manage.bookings_select_row", {
                          company: booking.company.name,
                        })}
                        checked={selectedIds.includes(booking.id)}
                        onChange={(event) =>
                          toggleSelection(
                            booking.id,
                            event.currentTarget.checked,
                          )
                        }
                      />
                    </Table.Td>
                    <Table.Td>
                      <Anchor
                        component={NavLink}
                        to={`/kp/${eventId}/bookings/${booking.id}`}
                      >
                        {booking.company.name}
                      </Anchor>
                    </Table.Td>
                    <Table.Td>{booking.booth_zone.name}</Table.Td>
                    <Table.Td>
                      <BoothNumberCell
                        boothNr={booking.booth_nr}
                        disabled={actions.isUpdating}
                        onSave={(boothNr) => {
                          void actions
                            .updateBooking(booking.id, { booth_nr: boothNr })
                            .catch(() => undefined);
                        }}
                      />
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs" wrap="nowrap">
                        <KpBookingStatusBadge status={booking.status} />
                        {hasNewAdditions(booking) ? (
                          <BookingNewAdditionsBadge />
                        ) : null}
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <BookingCompletenessIcon
                        isComplete={booking.is_complete ?? false}
                        missingItems={booking.missing_items ?? []}
                        services={booking.services ?? []}
                      />
                    </Table.Td>
                    <Table.Td>{booking.waitlist_count}</Table.Td>
                    <Table.Td>{`CHF ${formatPrice(booking.price.gross)}`}</Table.Td>
                    <Table.Td>
                      {formatBookingTimestamp(booking.status_changed_at) ?? "-"}
                    </Table.Td>
                    <Table.Td>
                      <BookingRowActions
                        onAction={(action) => handleRowAction(action, booking)}
                        status={booking.status}
                      />
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}

        {pageCount > 1 ? (
          <Group justify="space-between">
            <Text c="dimmed" size="sm">
              {t("kp.manage.bookings_page_summary", {
                shown: pageRows.length,
                total: visibleRows.length,
              })}
            </Text>
            <Pagination
              onChange={setPage}
              total={pageCount}
              value={currentPage}
            />
          </Group>
        ) : null}
      </Stack>

      <BookingConfirmModal
        body={t("kp.manage.booking_accept_body")}
        color="green"
        isPending={actions.isAccepting}
        onClose={() => setActiveAction(null)}
        onConfirm={() => {
          if (!activeBooking) return;
          void runAction(() => actions.acceptBooking(activeBooking.id));
        }}
        opened={activeAction?.kind === "accept"}
        submitLabel={t("kp.manage.booking_accept_submit")}
        title={t("kp.manage.booking_accept_title")}
      />
      <BookingConfirmModal
        body={t("kp.manage.booking_undo_accept_body")}
        isPending={actions.isUndoingAccept}
        onClose={() => setActiveAction(null)}
        onConfirm={() => {
          if (!activeBooking) return;
          void runAction(() => actions.undoAcceptBooking(activeBooking.id));
        }}
        opened={activeAction?.kind === "undo_accept"}
        submitLabel={t("kp.manage.booking_undo_accept_submit")}
        title={t("kp.manage.booking_undo_accept_title")}
      />
      <BookingRejectModal
        isPending={actions.isRejecting}
        onClose={() => setActiveAction(null)}
        onConfirm={(reason) => {
          if (!activeBooking) return;
          void runAction(() => actions.rejectBooking(activeBooking.id, reason));
        }}
        opened={activeAction?.kind === "reject"}
      />
      <BookingDeleteModal
        isPending={actions.isDeleting}
        onClose={() => setActiveAction(null)}
        onConfirm={(force) => {
          if (!activeBooking) return;
          void runAction(() => actions.deleteBooking(activeBooking.id, force));
        }}
        opened={activeAction?.kind === "delete"}
        requiresForce={
          activeBooking ? deleteRequiresForce(activeBooking.status) : false
        }
      />
    </Paper>
  );
};

export default BookingsTab;
