import {
  Anchor,
  Button,
  Center,
  Checkbox,
  Group,
  Loader,
  MultiSelect,
  Pagination,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { IconDownload, IconGift, IconSearch } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useNavigate } from "react-router";
import { KpBookingStatusBadge } from "./KpBookingStatusBadge";
import SortableHeader from "./SortableHeader";
import BookingNewAdditionsBadge from "./bookings/BookingNewAdditionsBadge";
import BookingCompletenessIcon from "./bookings/BookingCompletenessIcon";
import BookingConfirmModal from "./bookings/BookingConfirmModal";
import BookingDeleteModal from "./bookings/BookingDeleteModal";
import OfferBookingModal from "./bookings/OfferBookingModal";
import BookingRejectModal from "./bookings/BookingRejectModal";
import BookingRowActions, {
  type BookingRowActionKind,
} from "./bookings/BookingRowActions";
import BoothNumberCell from "./bookings/BoothNumberCell";
import ServiceFilterSelect from "./bookings/ServiceFilterSelect";
import { bookedAnyService } from "./bookings/service-filter";
import { formatBookingTimestamp } from "./bookings/booking-format";
import { useBookingActions } from "./bookings/useBookingActions";
import {
  downloadEventBookingsCsv,
  type ListEventBookingsQueryResult,
  useListEventBookings,
} from "../orval/generated/kp/kp";
import { KpBookingStatus } from "../orval/generated/fastAPI.schemas";
import {
  BOOKING_STATUS_ORDER,
  bookingStatusRank,
  hasNewAdditions,
  canAcceptBooking,
  deleteRequiresForce,
} from "../utils/booking-status";
import { downloadBlob } from "../utils/download";
import {
  BOOKING_STATUS_LABEL_KEYS,
  formatKpDisplayDate,
} from "../utils/kp-utils";
import { formatPrice } from "../utils/price-utils";
import { sortRows, useSort, type SortValue } from "../utils/sort";

type BookingRow = ListEventBookingsQueryResult[number];
type SortField =
  | "company"
  | "zone"
  | "booth"
  | "status"
  | "complete"
  | "waitlist"
  | "total"
  | "changed";

const ALL_STATUSES = "ALL";
const PAGE_SIZE = 25;

const SORT_COLUMNS: [SortField, string, number?][] = [
  ["company", "kp.manage.booking_company"],
  ["zone", "kp.manage.booking_booth_zone"],
  ["booth", "kp.manage.booking_booth_nr", 110],
  ["status", "kp.manage.booking_status"],
  ["complete", "kp.manage.booking_completeness", 110],
  ["waitlist", "kp.manage.booking_waitlist", 90],
  ["total", "kp.manage.booking_gross_total"],
  ["changed", "kp.manage.booking_status_changed_at"],
];

const SORT_VALUES: Record<SortField, (booking: BookingRow) => SortValue[]> = {
  company: () => [],
  zone: (booking) => [booking.booth_zone.order, booking.booth_zone.name],
  booth: (booking) => [booking.booth_nr],
  status: (booking) => [bookingStatusRank(booking.status)],
  complete: (booking) => [Number(booking.is_complete ?? false)],
  waitlist: (booking) => [booking.waitlist_count],
  total: (booking) => [booking.price.gross],
  changed: (booking) => [booking.status_changed_at],
};

const BookingsTab = ({
  eventId,
  canOffer = false,
}: {
  eventId: string;
  canOffer?: boolean;
}) => {
  const { t } = useTranslation();
  const [isOfferOpen, setIsOfferOpen] = useState(false);
  const navigate = useNavigate();
  const { data: bookings, isLoading } = useListEventBookings(eventId);
  const actions = useBookingActions(eventId);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>(ALL_STATUSES);
  const [incompleteOnly, setIncompleteOnly] = useState(false);
  const [serviceFilter, setServiceFilter] = useState<string[]>([]);
  const [zoneFilter, setZoneFilter] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const { sort, toggleSort } = useSort<SortField>(
    { field: "company", direction: "asc" },
    () => setPage(1),
  );
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeAction, setActiveAction] = useState<{
    booking: BookingRow;
    kind: Exclude<BookingRowActionKind, "open">;
  } | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  const rows = useMemo(() => bookings ?? [], [bookings]);
  const zoneOptions = useMemo(
    () =>
      [
        ...new Map(
          rows.map((booking) => [booking.booth_zone_id, booking.booth_zone]),
        ).values(),
      ]
        .sort(
          (left, right) =>
            left.order - right.order || left.name.localeCompare(right.name),
        )
        .map((zone) => ({ value: zone.id, label: zone.name })),
    [rows],
  );
  const bookedServices = useMemo(
    () =>
      rows.flatMap((booking) =>
        (booking.services ?? []).map((entry) => entry.service),
      ),
    [rows],
  );
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
      if (zoneFilter.length > 0 && !zoneFilter.includes(booking.booth_zone_id)) {
        return false;
      }
      return bookedAnyService(booking.services ?? [], serviceFilter);
    });

    return sortRows(filtered, sort, (booking, field) => [
      ...SORT_VALUES[field](booking),
      booking.company.name,
    ]);
  }, [
    incompleteOnly,
    rows,
    search,
    serviceFilter,
    sort,
    statusFilter,
    zoneFilter,
  ]);

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
            {canOffer ? (
              <Button
                leftSection={<IconGift size={16} />}
                onClick={() => setIsOfferOpen(true)}
                variant="default"
              >
                {t("kp.manage.offer_button")}
              </Button>
            ) : null}
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
          {zoneOptions.length > 0 ? (
            <MultiSelect
              clearable
              searchable
              data={zoneOptions}
              label={t("kp.manage.bookings_filter_zones")}
              onChange={(value) => {
                setPage(1);
                setZoneFilter(value);
              }}
              placeholder={t("kp.manage.bookings_filter_zones_all")}
              value={zoneFilter}
              w={220}
            />
          ) : null}
          {bookedServices.length > 0 ? (
            <ServiceFilterSelect
              label={t("kp.manage.bookings_filter_services")}
              onChange={(value) => {
                setPage(1);
                setServiceFilter(value);
              }}
              placeholder={t("kp.manage.bookings_filter_services_all")}
              services={bookedServices}
              value={serviceFilter}
              w={280}
            />
          ) : null}
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
                  {SORT_COLUMNS.map(([field, labelKey, width]) => (
                    <SortableHeader
                      key={field}
                      w={width}
                      field={field}
                      label={t(labelKey)}
                      sort={sort}
                      onSort={toggleSort}
                    />
                  ))}
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
                      <Group gap={4} preventGrowOverflow={false}>
                        <KpBookingStatusBadge
                          status={booking.status}
                          miw="max-content"
                        />
                        {hasNewAdditions(booking) ? (
                          <BookingNewAdditionsBadge />
                        ) : null}
                        {booking.status === KpBookingStatus.OFFERED &&
                        booking.offer_deadline ? (
                          <Text size="xs" c="dimmed">
                            {t("kp.manage.offer_until", {
                              date: formatKpDisplayDate(booking.offer_deadline),
                            })}
                          </Text>
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
      {canOffer ? (
        <OfferBookingModal
          eventId={eventId}
          opened={isOfferOpen}
          onClose={() => setIsOfferOpen(false)}
        />
      ) : null}
    </Paper>
  );
};

export default BookingsTab;
