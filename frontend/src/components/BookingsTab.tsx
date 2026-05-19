import { ActionIcon, Paper, Stack, Text, Title, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCheck } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { KpBookingStatusBadge } from "./KpBookingStatusBadge";
import { KpBookingStatus } from "../orval/generated/fastAPI.schemas";
import {
  getListEventBookingsQueryKey,
  type ListEventBookingsQueryResult,
  useConfirmBooking,
  useListEventBookings,
} from "../orval/generated/kp/kp";
import DataTable, { type DataTableColumn } from "./DataTable";

type BookingRow = ListEventBookingsQueryResult[number];

const BookingsTab = ({ eventId }: { eventId: string }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [confirmingBookingId, setConfirmingBookingId] = useState<string | null>(
    null,
  );
  const { data: bookings, isLoading } = useListEventBookings(eventId);
  const { mutate: confirmBooking, isPending: isConfirming } = useConfirmBooking(
    {
      mutation: {
        onSuccess: async () => {
          await queryClient.invalidateQueries({
            queryKey: getListEventBookingsQueryKey(eventId),
          });
          notifications.show({
            color: "green",
            message: t("kp.manage.booking_confirmed"),
          });
        },
        onSettled: () => {
          setConfirmingBookingId(null);
        },
      },
    },
  );

  const handleConfirmBooking = (bookingId: string) => {
    if (!confirm(t("kp.manage.booking_confirm_prompt"))) return;
    setConfirmingBookingId(bookingId);
    confirmBooking({ bookingId });
  };

  const columns: DataTableColumn<BookingRow>[] = [
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
    {
      key: "actions",
      header: t("kp.manage.booking_actions"),
      render: (booking) => {
        const canConfirm = booking.status === KpBookingStatus.FINALIZED;
        if (!canConfirm) {
          return (
            <Text c="dimmed" size="sm">
              -
            </Text>
          );
        }

        return (
          <Tooltip label={t("kp.manage.booking_confirm")}>
            <ActionIcon
              aria-label={t("kp.manage.booking_confirm")}
              color="green"
              disabled={isConfirming}
              loading={confirmingBookingId === booking.id}
              onClick={() => handleConfirmBooking(booking.id)}
              size="sm"
              variant="light"
            >
              <IconCheck size={16} />
            </ActionIcon>
          </Tooltip>
        );
      },
      width: 90,
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
