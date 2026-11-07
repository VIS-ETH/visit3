import {
  ActionIcon,
  Alert,
  Card,
  Group,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconArrowDown,
  IconArrowUp,
  IconHourglass,
  IconTrash,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import {
  KpBookingStatus,
  type BookingResponse,
  type BookingUpgradeWaitlistEntryResponse,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  getListBookingUpgradeWaitlistQueryKey,
  useListBookingUpgradeWaitlist,
  useReplaceBookingUpgradeWaitlist,
} from "../../orval/generated/kp/kp";
import { useAsyncAction } from "../../hooks/use-async-action";
import { formatMoney } from "../../utils/money";
import { notifySuccess } from "../../utils/notify";
import { priceBreakdown } from "../../utils/pricing";
import { swapped } from "../../utils/swapped";
import ErrorAlert from "../ErrorAlert";
import { KpBoothZoneColorSwatch } from "../KpBoothZoneColorSwatch";
import PageLoader from "../PageLoader";
import { INLINE_ERROR_REQUEST } from "./inline-error-request";

interface WaitlistCardProps {
  event: KpResponse;
  booking: BookingResponse;
}

const WaitlistCard = ({ event, booking }: WaitlistCardProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const isRegistered = booking.status === KpBookingStatus.REGISTERED;

  const {
    data: entries,
    isLoading,
    isError,
  } = useListBookingUpgradeWaitlist(booking.id, {
    query: { enabled: isRegistered },
  });
  const { mutateAsync: replaceWaitlist } = useReplaceBookingUpgradeWaitlist({
    request: INLINE_ERROR_REQUEST,
  });
  const { run: submit, isRunning: isPending } = useAsyncAction(
    async (targetBoothZoneIds: string[], message: string) => {
      setErrorCode(null);
      const queryKey = getListBookingUpgradeWaitlistQueryKey(booking.id);
      const updated = await replaceWaitlist({
        bookingId: booking.id,
        data: { target_booth_zone_ids: targetBoothZoneIds },
      });
      queryClient.setQueryData(queryKey, updated);
      notifySuccess(message);
      await queryClient.invalidateQueries({ queryKey });
    },
    (error) => setErrorCode(getApiErrorCode(error) ?? "server.error"),
  );

  if (!isRegistered) return null;

  const zoneIds = (entries ?? []).map((entry) => entry.target_booth_zone_id);

  const move = (index: number, target: number) =>
    void submit(swapped(zoneIds, index, target), t("kp.waitlist.reordered"));

  const remove = (entry: BookingUpgradeWaitlistEntryResponse) =>
    void submit(
      zoneIds.filter((zoneId) => zoneId !== entry.target_booth_zone_id),
      t("kp.waitlist.removed", { zone: entry.target_booth_zone.name }),
    );

  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="sm">
        <Group gap="sm">
          <IconHourglass size={22} />
          <Title order={4}>{t("kp.waitlist.title")}</Title>
        </Group>
        <Text c="dimmed" size="sm">
          {t("kp.waitlist.description")}
        </Text>

        {errorCode ? (
          <Alert icon={<IconAlertCircle />} color="red">
            {t(errorCode)}
          </Alert>
        ) : null}

        {isError ? (
          <ErrorAlert />
        ) : isLoading ? (
          <PageLoader />
        ) : entries && entries.length > 0 ? (
          <Stack gap="xs">
            {entries.map((entry, index) => (
              <Card key={entry.id} withBorder radius="md" p="sm">
                <Group justify="space-between" wrap="nowrap">
                  <Group gap="xs" wrap="nowrap">
                    <KpBoothZoneColorSwatch
                      color={entry.target_booth_zone.color}
                    />
                    <Text fw={600} size="sm">
                      {entry.target_booth_zone.name}
                    </Text>
                  </Group>
                  <Group gap={4} wrap="nowrap">
                    <ActionIcon
                      variant="subtle"
                      aria-label={t("kp.waitlist.move_up")}
                      disabled={index === 0 || isPending}
                      onClick={() => move(index, index - 1)}
                    >
                      <IconArrowUp size={16} />
                    </ActionIcon>
                    <ActionIcon
                      variant="subtle"
                      aria-label={t("kp.waitlist.move_down")}
                      disabled={index === entries.length - 1 || isPending}
                      onClick={() => move(index, index + 1)}
                    >
                      <IconArrowDown size={16} />
                    </ActionIcon>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      aria-label={t("kp.waitlist.remove")}
                      disabled={isPending}
                      onClick={() => remove(entry)}
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                  </Group>
                </Group>
                <Group gap="md" mt={4} wrap="wrap">
                  <Text size="xs" fw={500}>
                    {t("kp.waitlist.position", { position: entry.position })}
                  </Text>
                  <Text size="xs" c={entry.is_full ? "dimmed" : "green"}>
                    {entry.is_full
                      ? t("kp.waitlist.zone_full")
                      : t("kp.booth_size", {
                          size: entry.target_booth_zone.booth_size,
                        })}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {t("kp.waitlist.price_net", {
                      amount: formatMoney(entry.target_booth_zone.base_price),
                    })}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {t("kp.waitlist.price_gross", {
                      amount: formatMoney(
                        priceBreakdown(
                          entry.target_booth_zone.base_price,
                          event.vat_rate_percent,
                        ).gross,
                      ),
                    })}
                  </Text>
                </Group>
              </Card>
            ))}
          </Stack>
        ) : (
          <Stack gap={4}>
            <Text size="sm">{t("kp.waitlist.empty")}</Text>
            <Text size="sm" c="dimmed">
              {t("kp.waitlist.empty_hint")}
            </Text>
          </Stack>
        )}
      </Stack>
    </Card>
  );
};

export default WaitlistCard;
