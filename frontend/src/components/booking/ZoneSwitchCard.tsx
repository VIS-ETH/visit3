import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  ScrollArea,
  Stack,
  Text,
  Title,
  UnstyledButton,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconArrowsExchange } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  getGetEventVenueQueryKey,
  getGetMyBookingQueryKey,
  getListAvailableBoothZonesQueryKey,
  getListBookingUpgradeWaitlistQueryKey,
  useListAvailableBoothZones,
  useListBookingUpgradeWaitlist,
  useReplaceBookingUpgradeWaitlist,
  useSwitchBookingZone,
} from "../../orval/generated/kp/kp";
import { formatPrice } from "../../utils/price-utils";
import { priceBreakdown } from "../../utils/pricing";
import { KpBoothZoneColorSwatch } from "../KpBoothZoneColorSwatch";
import VenueMapViewer from "../venue/VenueMapViewer";
import {
  canSwitchBoothZone,
  isFinalizationDeadlinePassed,
} from "./booking-zone-access";

const signedPrice = (cents: number) =>
  `${cents < 0 ? "-" : "+"}${formatPrice(Math.abs(cents))}`;

interface ZoneSwitchCardProps {
  event: KpResponse;
  booking: BookingResponse;
}

const ZoneSwitchCard = ({ event, booking }: ZoneSwitchCardProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isModalOpen, setModalOpen] = useState(false);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [isConfirming, setConfirming] = useState(false);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const canSwitch = canSwitchBoothZone(event, booking);
  const { data: zones, isLoading: isLoadingZones } = useListAvailableBoothZones(
    event.id,
  );
  const { data: waitlistEntries } = useListBookingUpgradeWaitlist(booking.id, {
    query: { enabled: canSwitch },
  });
  const { mutateAsync: switchZone, isPending: isSwitching } =
    useSwitchBookingZone();
  const { mutateAsync: replaceWaitlist, isPending: isJoiningWaitlist } =
    useReplaceBookingUpgradeWaitlist();

  const currentZone = zones?.find((zone) => zone.id === booking.booth_zone_id);
  const currentBasePrice =
    currentZone?.base_price ?? booking.booth_zone?.base_price ?? 0;
  const otherZones = (zones ?? []).filter(
    (zone) => zone.id !== booking.booth_zone_id,
  );
  const selectedZone =
    otherZones.find((zone) => zone.id === selectedZoneId) ?? null;
  const waitlistedZoneIds = (waitlistEntries ?? []).map(
    (entry) => entry.target_booth_zone_id,
  );

  const closeModal = () => {
    setModalOpen(false);
    setSelectedZoneId(null);
    setConfirming(false);
    setErrorCode(null);
  };

  const pickZone = (zoneId: string) => {
    setSelectedZoneId(zoneId);
    setConfirming(false);
    setErrorCode(null);
  };

  const refreshBooking = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetMyBookingQueryKey(event.id),
      }),
      queryClient.invalidateQueries({
        queryKey: getListAvailableBoothZonesQueryKey(event.id),
      }),
      queryClient.invalidateQueries({
        queryKey: getGetEventVenueQueryKey(event.id),
      }),
      queryClient.invalidateQueries({
        queryKey: getListBookingUpgradeWaitlistQueryKey(booking.id),
      }),
    ]);
  };

  const submitSwitch = async (zone: BoothZoneWithAvailabilityResponse) => {
    try {
      await switchZone({
        bookingId: booking.id,
        data: { booth_zone_id: zone.id },
      });
    } catch (error) {
      setErrorCode(getApiErrorCode(error) ?? "server.error");
      return;
    }
    await refreshBooking();
    notifications.show({
      color: "green",
      message: t("kp.zone_switch.switched", { zone: zone.name }),
    });
    closeModal();
  };

  const submitWaitlist = async (zone: BoothZoneWithAvailabilityResponse) => {
    try {
      await replaceWaitlist({
        bookingId: booking.id,
        data: { target_booth_zone_ids: [...waitlistedZoneIds, zone.id] },
      });
    } catch (error) {
      setErrorCode(getApiErrorCode(error) ?? "server.error");
      return;
    }
    await queryClient.invalidateQueries({
      queryKey: getListBookingUpgradeWaitlistQueryKey(booking.id),
    });
    notifications.show({
      color: "green",
      message: t("kp.zone_switch.waitlist_added", { zone: zone.name }),
    });
    closeModal();
  };

  const zoneDifference = (zone: BoothZoneWithAvailabilityResponse) => {
    const net = zone.base_price - currentBasePrice;
    if (net === 0) return t("kp.zone_switch.price_same");
    return t("kp.zone_switch.price_difference", {
      net: signedPrice(net),
      gross: signedPrice(priceBreakdown(net, event.vat_rate_percent).gross),
      currency: t("common.currency"),
    });
  };

  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="sm">
        <Group gap="sm">
          <IconArrowsExchange size={22} />
          <Title order={4}>{t("kp.zone_switch.title")}</Title>
        </Group>
        <Text c="dimmed" size="sm">
          {t("kp.zone_switch.description")}
        </Text>

        <Group gap="xs" align="center">
          <Text size="sm" c="dimmed">
            {t("kp.zone_switch.current_zone")}
          </Text>
          {booking.booth_zone ? (
            <KpBoothZoneColorSwatch color={booking.booth_zone.color} />
          ) : null}
          <Text fw={500}>
            {booking.booth_zone?.name ?? booking.booth_zone_id}
          </Text>
        </Group>
        <Group gap="md">
          <Text size="sm">
            {t("kp.zone_switch.price_net", {
              amount: formatPrice(currentBasePrice),
              currency: t("common.currency"),
            })}
          </Text>
          <Text size="sm">
            {t("kp.zone_switch.price_gross", {
              amount: formatPrice(
                priceBreakdown(currentBasePrice, event.vat_rate_percent).gross,
              ),
              currency: t("common.currency"),
            })}
          </Text>
          {currentZone ? (
            <Text
              size="sm"
              c={currentZone.available_spots > 0 ? "green" : "red"}
            >
              {currentZone.available_spots > 0
                ? t("kp.zone_switch.spots_free", {
                    free: currentZone.available_spots,
                    capacity: currentZone.capacity,
                  })
                : t("kp.zone_switch.zone_full")}
            </Text>
          ) : null}
        </Group>

        {canSwitch ? null : (
          <Text size="sm" c="dimmed">
            {t(
              isFinalizationDeadlinePassed(event)
                ? "kp.zone_switch.disabled_deadline"
                : "kp.zone_switch.disabled_status",
            )}
          </Text>
        )}

        <Group>
          <Button
            variant="light"
            disabled={!canSwitch}
            leftSection={<IconArrowsExchange size={18} />}
            onClick={() => setModalOpen(true)}
          >
            {t("kp.zone_switch.open")}
          </Button>
        </Group>
      </Stack>

      <Modal
        centered
        size="xl"
        opened={isModalOpen}
        onClose={closeModal}
        title={t("kp.zone_switch.modal_title")}
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            {t("kp.zone_switch.map_hint")}
          </Text>
          <VenueMapViewer
            eventId={event.id}
            selectedZoneId={selectedZoneId}
            onSelectZone={pickZone}
            viewHeight={280}
          />

          {errorCode ? (
            <Alert icon={<IconAlertCircle />} color="red">
              {t(errorCode)}
            </Alert>
          ) : null}

          {isLoadingZones ? (
            <Center py="md">
              <Loader />
            </Center>
          ) : otherZones.length === 0 ? (
            <Text c="dimmed" size="sm">
              {t("kp.zone_switch.no_zones")}
            </Text>
          ) : (
            <ScrollArea.Autosize mah={280} type="auto" offsetScrollbars>
              <Stack
                gap="xs"
                pr={8}
                role="group"
                aria-label={t("kp.zone_switch.zone_list")}
              >
                {otherZones.map((zone) => {
                  const isFull = zone.available_spots <= 0;
                  const isSelected = zone.id === selectedZoneId;
                  return (
                    <UnstyledButton
                      key={zone.id}
                      aria-pressed={isSelected}
                      onClick={() => pickZone(zone.id)}
                    >
                      <Card
                        withBorder
                        radius="md"
                        p="sm"
                        style={{
                          borderColor: isSelected
                            ? "var(--mantine-color-brand-5)"
                            : undefined,
                          borderWidth: isSelected ? 2 : 1,
                        }}
                      >
                        <Group justify="space-between" wrap="nowrap">
                          <Group gap="xs" wrap="nowrap">
                            <KpBoothZoneColorSwatch color={zone.color} />
                            <Text fw={600} size="sm">
                              {zone.name}
                            </Text>
                            {waitlistedZoneIds.includes(zone.id) ? (
                              <Badge color="blue" size="sm" variant="light">
                                {t("kp.zone_switch.already_waitlisted")}
                              </Badge>
                            ) : null}
                          </Group>
                          <Text size="xs" c={isFull ? "red" : "green"}>
                            {isFull
                              ? t("kp.zone_switch.zone_full")
                              : t("kp.zone_switch.spots_free", {
                                  free: zone.available_spots,
                                  capacity: zone.capacity,
                                })}
                          </Text>
                        </Group>
                        <Group justify="space-between" mt={4} wrap="nowrap">
                          <Text size="xs" c="dimmed">
                            {t("kp.zone_switch.price_net", {
                              amount: formatPrice(zone.base_price),
                              currency: t("common.currency"),
                            })}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {zoneDifference(zone)}
                          </Text>
                        </Group>
                      </Card>
                    </UnstyledButton>
                  );
                })}
              </Stack>
            </ScrollArea.Autosize>
          )}

          {selectedZone === null ? null : selectedZone.available_spots > 0 ? (
            isConfirming ? (
              <Stack gap="xs">
                <Text size="sm">
                  {t("kp.zone_switch.confirm_body", {
                    zone: selectedZone.name,
                  })}
                </Text>
                <Group justify="flex-end">
                  <Button variant="subtle" onClick={() => setConfirming(false)}>
                    {t("common.cancel")}
                  </Button>
                  <Button
                    loading={isSwitching}
                    onClick={() => void submitSwitch(selectedZone)}
                  >
                    {t("kp.zone_switch.confirm_submit")}
                  </Button>
                </Group>
              </Stack>
            ) : (
              <Group justify="flex-end">
                <Button onClick={() => setConfirming(true)}>
                  {t("kp.zone_switch.switch_action")}
                </Button>
              </Group>
            )
          ) : (
            <Group justify="flex-end">
              <Button
                loading={isJoiningWaitlist}
                disabled={waitlistedZoneIds.includes(selectedZone.id)}
                onClick={() => void submitWaitlist(selectedZone)}
              >
                {t("kp.zone_switch.waitlist_action")}
              </Button>
            </Group>
          )}
        </Stack>
      </Modal>
    </Card>
  );
};

export default ZoneSwitchCard;
