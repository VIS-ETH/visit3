import {
  Alert,
  Badge,
  Group,
  List,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconNote } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import { useMissingItemLabel } from "./missing-items";

const BookingCompletenessCard = ({
  booking,
}: {
  booking: StaffBookingResponse;
}) => {
  const { t } = useTranslation();
  const missingItemLabel = useMissingItemLabel(booking.services ?? []);
  const missingItems = booking.missing_items ?? [];
  const isComplete = booking.is_complete ?? false;

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Title order={4}>{t("kp.manage.booking_detail_completion")}</Title>
          <Badge color={isComplete ? "green" : "yellow"} variant="light">
            {isComplete
              ? t("kp.manage.booking_completeness_complete")
              : t("kp.manage.booking_completeness_incomplete")}
          </Badge>
        </Group>

        {isComplete ? (
          <Text c="dimmed" size="sm">
            {t("kp.manage.booking_complete")}
          </Text>
        ) : (
          <Stack gap="xs">
            <Text size="sm">{t("kp.manage.booking_incomplete")}</Text>
            <List size="sm" withPadding>
              {missingItems.map((item) => (
                <List.Item key={item}>{missingItemLabel(item)}</List.Item>
              ))}
            </List>
          </Stack>
        )}

        {booking.rejection_reason ? (
          <Alert
            color="red"
            icon={<IconAlertCircle />}
            title={t("kp.manage.booking_rejection_reason")}
          >
            {booking.rejection_reason}
          </Alert>
        ) : null}

        {booking.status_note ? (
          <Alert
            color="blue"
            icon={<IconNote />}
            title={t("kp.manage.booking_status_note")}
          >
            {booking.status_note}
          </Alert>
        ) : null}
      </Stack>
    </Paper>
  );
};

export default BookingCompletenessCard;
