import { Center, Loader, Stack, Table, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { KpBookingStatusBadge } from "../../components/KpBookingStatusBadge";
import { useListEventBookings } from "../../orval/generated/kp/kp";

export default function BookingsTab({ eventId }: { eventId: string }) {
  const { t } = useTranslation();
  const { data: bookings, isLoading } = useListEventBookings(eventId);

  if (isLoading) {
    return (
      <Center py="md">
        <Loader />
      </Center>
    );
  }

  return (
    <Stack gap="md">
      <Title order={4}>{t("kp.manage.bookings_title")}</Title>
      {bookings && bookings.length > 0 ? (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t("kp.manage.booking_company")}</Table.Th>
              <Table.Th>{t("kp.manage.booking_booth_zone")}</Table.Th>
              <Table.Th>{t("kp.manage.booking_booth_nr")}</Table.Th>
              <Table.Th>{t("kp.manage.booking_status")}</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {bookings.map((booking) => (
              <Table.Tr key={booking.id}>
                <Table.Td>{booking.company.name}</Table.Td>
                <Table.Td>{booking.booth_zone.name}</Table.Td>
                <Table.Td>{booking.booth_nr ?? "-"}</Table.Td>
                <Table.Td>
                  <KpBookingStatusBadge status={booking.status} />
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed">{t("kp.manage.bookings_empty")}</Text>
      )}
    </Stack>
  );
}
