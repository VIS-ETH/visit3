import {
  ActionIcon,
  Alert,
  Card,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
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
import { formatPrice } from "../../utils/price-utils";
import { priceBreakdown } from "../../utils/pricing";
import { KpBoothZoneColorSwatch } from "../KpBoothZoneColorSwatch";

const swapped = (zoneIds: string[], index: number, target: number) => {
  const reordered = [...zoneIds];
  [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
  return reordered;
};

interface WaitlistCardProps {
  event: KpResponse;
  booking: BookingResponse;
}

const WaitlistCard = ({ event, booking }: WaitlistCardProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const isRegistered = booking.status === KpBookingStatus.REGISTERED;

  const { data: entries, isLoading } = useListBookingUpgradeWaitlist(
    booking.id,
    { query: { enabled: isRegistered } },
  );
  const { mutateAsync: replaceWaitlist, isPending } =
    useReplaceBookingUpgradeWaitlist();

  if (!isRegistered) return null;

  const zoneIds = (entries ?? []).map((entry) => entry.target_booth_zone_id);

  const submit = async (
    targetBoothZoneIds: string[],
    message: string,
  ): Promise<void> => {
    setErrorCode(null);
    try {
      await replaceWaitlist({
        bookingId: booking.id,
        data: { target_booth_zone_ids: targetBoothZoneIds },
      });
    } catch (error) {
      setErrorCode(getApiErrorCode(error) ?? "server.error");
      return;
    }
    await queryClient.invalidateQueries({
      queryKey: getListBookingUpgradeWaitlistQueryKey(booking.id),
    });
    notifications.show({ color: "green", message });
  };

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

        {isLoading ? (
          <Center py="md">
            <Loader />
          </Center>
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
                  <Text
                    size="xs"
                    c={entry.available_spots > 0 ? "green" : "dimmed"}
                  >
                    {entry.available_spots > 0
                      ? t("kp.waitlist.spots_free", {
                          free: entry.available_spots,
                          capacity: entry.target_booth_zone.capacity,
                        })
                      : t("kp.waitlist.zone_full")}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {t("kp.waitlist.price_net", {
                      amount: formatPrice(entry.target_booth_zone.base_price),
                      currency: t("common.currency"),
                    })}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {t("kp.waitlist.price_gross", {
                      amount: formatPrice(
                        priceBreakdown(
                          entry.target_booth_zone.base_price,
                          event.vat_rate_percent,
                        ).gross,
                      ),
                      currency: t("common.currency"),
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
