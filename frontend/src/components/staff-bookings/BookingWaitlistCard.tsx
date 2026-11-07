import {
  Alert,
  Badge,
  Center,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import { useListStaffBookingUpgradeWaitlist } from "../../orval/generated/kp/kp";

const BookingWaitlistCard = ({
  booking,
}: {
  booking: StaffBookingResponse;
}) => {
  const { t } = useTranslation();
  const hasWaitlistEntries = booking.waitlist_count > 0;
  const {
    data: entries,
    isError,
    isLoading,
  } = useListStaffBookingUpgradeWaitlist(booking.id, {
    query: { enabled: hasWaitlistEntries },
  });

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Title order={4}>{t("kp.manage.booking_waitlist_title")}</Title>
          <Badge variant="light">
            {t("kp.manage.booking_waitlist_count", {
              amount: booking.waitlist_count,
            })}
          </Badge>
        </Group>

        {!hasWaitlistEntries ? (
          <Text c="dimmed">{t("kp.manage.booking_waitlist_empty")}</Text>
        ) : isLoading ? (
          <Center py="md">
            <Loader />
          </Center>
        ) : isError || !entries ? (
          <Alert color="red" icon={<IconAlertCircle />}>
            {t("kp.manage.booking_waitlist_error")}
          </Alert>
        ) : (
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("kp.manage.booking_waitlist_zone")}</Table.Th>
                <Table.Th>{t("kp.manage.booking_waitlist_position")}</Table.Th>
                <Table.Th>{t("kp.manage.booking_waitlist_available")}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {entries.map((entry) => (
                <Table.Tr key={entry.id}>
                  <Table.Td>{entry.target_booth_zone.name}</Table.Td>
                  <Table.Td>{entry.position}</Table.Td>
                  <Table.Td>{entry.available_spots}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Stack>
    </Paper>
  );
};

export default BookingWaitlistCard;
