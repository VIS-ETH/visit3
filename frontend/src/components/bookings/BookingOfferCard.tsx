import {
  Alert,
  Button,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import {
  getGetEventBookingQueryKey,
  getListEventBookingsQueryKey,
  useUpdateBookingOffer,
} from "../../orval/generated/kp/kp";
import {
  formatKpDisplayDate,
  formatKpIsoDateInput,
  parseKpDateInput,
  toKpIsoDate,
} from "../../utils/kp-utils";

const BookingOfferCard = ({
  booking,
  eventId,
  canEdit,
}: {
  booking: StaffBookingResponse;
  eventId: string;
  canEdit: boolean;
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [deadline, setDeadline] = useState(
    formatKpIsoDateInput(booking.offer_cancel_until),
  );
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const { mutateAsync: update, isPending } = useUpdateBookingOffer();

  const save = async () => {
    setErrorCode(null);
    try {
      await update({
        bookingId: booking.id,
        data: { cancel_until: toKpIsoDate(deadline) },
      });
    } catch (error) {
      setErrorCode(getApiErrorCode(error) ?? "error.internal");
      return;
    }
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetEventBookingQueryKey(eventId, booking.id),
      }),
      queryClient.invalidateQueries({
        queryKey: getListEventBookingsQueryKey(eventId),
      }),
    ]);
    notifications.show({ color: "green", message: t("kp.manage.offer_saved") });
  };

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="sm">
        <Title order={4}>{t("kp.manage.offer_title")}</Title>
        <Text size="sm" c="dimmed">
          {t("kp.manage.offer_state", {
            date: formatKpDisplayDate(booking.offer_cancel_until ?? ""),
          })}
        </Text>
        {errorCode ? (
          <Alert color="red" icon={<IconAlertCircle />}>
            {t(errorCode)}
          </Alert>
        ) : null}
        {canEdit ? (
          <Group align="flex-end">
            <TextInput
              label={t("kp.manage.offer_cancel_until")}
              placeholder={t("kp.dashboard.date_input_placeholder")}
              value={deadline}
              onChange={(event) => setDeadline(event.currentTarget.value)}
              disabled={isPending}
            />
            <Button
              loading={isPending}
              disabled={parseKpDateInput(deadline) === null}
              onClick={() => void save()}
            >
              {t("kp.manage.offer_save")}
            </Button>
          </Group>
        ) : null}
      </Stack>
    </Paper>
  );
};

export default BookingOfferCard;
