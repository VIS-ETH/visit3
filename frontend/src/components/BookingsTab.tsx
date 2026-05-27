import { Paper, Stack, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { KpBookingStatusBadge } from "./KpBookingStatusBadge";
import {
  type ListEventBookingsQueryResult,
  useListEventBookings,
} from "../orval/generated/kp/kp";
import DataTable, { type DataTableColumn } from "./DataTable";

type BookingRow = ListEventBookingsQueryResult[number];

const BookingsTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: bookings, isLoading } = useListEventBookings(eventId);

  const columns: DataTableColumn<BookingRow>[] = [
    {
      key: "booking-number",
      header: t("kp.manage.booking_number"),
      render: (booking) => `#${booking.booking_number}`,
      searchableValue: (booking) => String(booking.booking_number),
      width: 110,
    },
    {
      key: "company",
      header: t("kp.manage.booking_company"),
      render: (booking) => booking.company.name,
      searchableValue: (booking) => booking.company.name,
    },
    {
      key: "booth-zone",
      header: t("kp.manage.booking_booth_zone"),
      render: (booking) => booking.booth_zone.name,
      searchableValue: (booking) => booking.booth_zone.name,
    },
    {
      key: "booth-number",
      header: t("kp.manage.booking_booth_nr"),
      render: (booking) => booking.booth_nr ?? "-",
      searchableValue: (booking) => String(booking.booth_nr ?? ""),
    },
    {
      key: "status",
      header: t("kp.manage.booking_status"),
      render: (booking) => <KpBookingStatusBadge status={booking.status} />,
      searchableValue: (booking) => booking.status,
    },
  ];

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="sm">
        <Title order={4}>{t("kp.manage.bookings_title")}</Title>
        <DataTable
          columns={columns}
          data={bookings}
          emptyLabel={t("kp.manage.bookings_empty")}
          getRowKey={(booking) => booking.id}
          isLoading={isLoading}
          onRowClick={(booking) =>
            navigate(`/kp/${eventId}/bookings/${booking.id}`)
          }
          pagination={{
            pageSummary: (first, last, total) =>
              t("kp.manage.bookings_page_summary", { first, last, total }),
            rowsPerPage: t("kp.manage.bookings_rows_per_page"),
          }}
          search={{
            noResults: t("kp.manage.bookings_no_results"),
            placeholder: t("kp.manage.bookings_search_placeholder"),
          }}
        />
      </Stack>
    </Paper>
  );
};
export default BookingsTab;
