import { Anchor, Checkbox, Group, Table, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router";
import {
  KpBookingStatus,
  type StaffBookingResponse,
} from "../../../orval/generated/fastAPI.schemas";
import { hasNewAdditions } from "../../../utils/booking-status";
import { formatKpDisplayDate } from "../../../utils/kp-utils";
import { formatMoney } from "../../../utils/money";
import type { SortState } from "../../../utils/sort";
import { KpBookingStatusBadge } from "../../KpBookingStatusBadge";
import SortableHeader from "../../SortableHeader";
import BookingCompletenessIcon from "../../staff-bookings/BookingCompletenessIcon";
import BookingNewAdditionsBadge from "../../staff-bookings/BookingNewAdditionsBadge";
import BookingRowActions, {
  type BookingRowActionKind,
} from "../../staff-bookings/BookingRowActions";
import BoothNumberCell from "../../staff-bookings/BoothNumberCell";
import { formatBookingTimestamp } from "../../staff-bookings/booking-format";
import type { BookingSortField } from "./use-booking-filters";

const SORT_COLUMNS: [BookingSortField, string, number?][] = [
  ["company", "kp.manage.booking_company"],
  ["zone", "kp.manage.booking_booth_zone"],
  ["booth", "kp.manage.booking_booth_nr", 110],
  ["status", "kp.manage.booking_status"],
  ["complete", "kp.manage.booking_completeness", 110],
  ["waitlist", "kp.manage.booking_waitlist", 90],
  ["total", "kp.manage.booking_gross_total"],
  ["registered", "kp.manage.booking_registered_at"],
  ["changed", "kp.manage.booking_status_changed_at"],
];

const BookingsTable = ({
  eventId,
  rows,
  sort,
  onSort,
  selectedIds,
  onSelectionChange,
  onAction,
  onSaveBoothNr,
}: {
  eventId: string;
  rows: StaffBookingResponse[];
  sort: SortState<BookingSortField> | null;
  onSort: (field: BookingSortField) => void;
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onAction: (
    action: BookingRowActionKind,
    booking: StaffBookingResponse,
  ) => void;
  onSaveBoothNr: (
    bookingId: string,
    boothNr: number | null,
  ) => Promise<unknown>;
}) => {
  const { t } = useTranslation();
  const rowIds = rows.map((booking) => booking.id);
  const selectedRowIds = rowIds.filter((id) => selectedIds.includes(id));

  const toggleRow = (bookingId: string, checked: boolean) =>
    onSelectionChange(
      checked
        ? [...selectedIds, bookingId]
        : selectedIds.filter((id) => id !== bookingId),
    );

  return (
    <Table.ScrollContainer minWidth={1100}>
      <Table highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th w={40}>
              <Checkbox
                aria-label={t("kp.manage.bookings_select_all")}
                checked={selectedRowIds.length === rowIds.length}
                indeterminate={
                  selectedRowIds.length > 0 &&
                  selectedRowIds.length < rowIds.length
                }
                onChange={(event) =>
                  onSelectionChange(event.currentTarget.checked ? rowIds : [])
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
                onSort={onSort}
              />
            ))}
            <Table.Th w={60}>{t("kp.manage.booking_actions")}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((booking) => (
            <Table.Tr key={booking.id}>
              <Table.Td>
                <Checkbox
                  aria-label={t("kp.manage.bookings_select_row", {
                    company: booking.company.name,
                  })}
                  checked={selectedIds.includes(booking.id)}
                  onChange={(event) =>
                    toggleRow(booking.id, event.currentTarget.checked)
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
                  onSave={(boothNr) => onSaveBoothNr(booking.id, boothNr)}
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
              <Table.Td>{formatMoney(booking.price.gross)}</Table.Td>
              <Table.Td>
                {formatBookingTimestamp(booking.created_at) ?? "-"}
              </Table.Td>
              <Table.Td>
                {formatBookingTimestamp(booking.status_changed_at) ?? "-"}
              </Table.Td>
              <Table.Td>
                <BookingRowActions
                  companyId={booking.company_id}
                  onAction={(action) => onAction(action, booking)}
                  status={booking.status}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
};

export default BookingsTable;
