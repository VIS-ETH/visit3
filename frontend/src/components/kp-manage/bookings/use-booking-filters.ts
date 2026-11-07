import { useMemo, useState } from "react";
import { useGetRecentChanges } from "../../../orval/generated/changes/changes";
import type { StaffBookingResponse } from "../../../orval/generated/fastAPI.schemas";
import { useOnlyChangesParam } from "../../../hooks/use-only-changes-param";
import { bookingStatusRank } from "../../../utils/booking-status";
import { sortRows, useSort, type SortValue } from "../../../utils/sort";
import { bookedAnyService } from "../../staff-bookings/service-filter";

export type BookingSortField =
  | "company"
  | "zone"
  | "booth"
  | "status"
  | "complete"
  | "waitlist"
  | "total"
  | "registered"
  | "changed";

export const ALL_STATUSES = "ALL";
const PAGE_SIZE = 25;

const SORT_VALUES: Record<
  BookingSortField,
  (booking: StaffBookingResponse) => SortValue[]
> = {
  company: () => [],
  zone: (booking) => [booking.booth_zone.order, booking.booth_zone.name],
  booth: (booking) => [booking.booth_nr],
  status: (booking) => [bookingStatusRank(booking.status)],
  complete: (booking) => [Number(booking.is_complete ?? false)],
  waitlist: (booking) => [booking.waitlist_count],
  total: (booking) => [booking.price.gross],
  registered: (booking) => [booking.created_at],
  changed: (booking) => [booking.status_changed_at],
};

const changedSince = (booking: StaffBookingResponse, since: Date | null) => {
  if (since === null) return true;
  const changedAt = booking.changed_at ?? booking.created_at;
  return changedAt != null && new Date(changedAt) > since;
};

export const useBookingFilters = (
  bookings: StaffBookingResponse[] | undefined,
) => {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>(ALL_STATUSES);
  const [incompleteOnly, setIncompleteOnly] = useState(false);
  const [serviceFilter, setServiceFilter] = useState<string[]>([]);
  const [zoneFilter, setZoneFilter] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [onlyChanges, setOnlyChanges] = useOnlyChangesParam(() => setPage(1));
  const { sort, toggleSort } = useSort<BookingSortField>(
    { field: "company", direction: "asc" },
    () => setPage(1),
  );
  const { data: recentChanges } = useGetRecentChanges({
    query: { enabled: onlyChanges },
  });
  const changesSince = useMemo(
    () => (recentChanges ? new Date(recentChanges.since) : null),
    [recentChanges],
  );

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
      if (onlyChanges && !changedSince(booking, changesSince)) return false;
      if (
        zoneFilter.length > 0 &&
        !zoneFilter.includes(booking.booth_zone_id)
      ) {
        return false;
      }
      return bookedAnyService(booking.services ?? [], serviceFilter);
    });

    const sorted = sortRows(filtered, sort, (booking, field) => [
      ...SORT_VALUES[field](booking),
      booking.company.name,
    ]);
    return onlyChanges
      ? [...sorted].sort((left, right) =>
          (right.changed_at ?? "").localeCompare(left.changed_at ?? ""),
        )
      : sorted;
  }, [
    changesSince,
    onlyChanges,
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

  const resettingPage =
    <Value>(setter: (value: Value) => void) =>
    (value: Value) => {
      setPage(1);
      setter(value);
    };

  return {
    bookedServices,
    currentPage,
    hasBookings: rows.length > 0,
    incompleteOnly,
    onlyChanges,
    pageCount,
    pageRows,
    search,
    serviceFilter,
    setIncompleteOnly: resettingPage(setIncompleteOnly),
    setOnlyChanges,
    setPage,
    setSearch: resettingPage(setSearch),
    setServiceFilter: resettingPage(setServiceFilter),
    setStatusFilter: resettingPage(setStatusFilter),
    setZoneFilter: resettingPage(setZoneFilter),
    sort,
    statusFilter,
    toggleSort,
    visibleRows,
    zoneFilter,
    zoneOptions,
  };
};

export type BookingFilters = ReturnType<typeof useBookingFilters>;
