import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  ScrollArea,
  Stack,
  Text,
  Title,
  UnstyledButton,
} from "@mantine/core";
import { notifySuccess } from "../../utils/notify";
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
import { useAsyncAction } from "../../hooks/use-async-action";
import { chargedServiceQuantity } from "../../utils/kp-service-quantity";
import { formatMoney } from "../../utils/money";
import { priceBreakdown } from "../../utils/pricing";
import ErrorAlert from "../ErrorAlert";
import { KpBoothZoneColorSwatch } from "../KpBoothZoneColorSwatch";
import PageLoader from "../PageLoader";
import FloorPlanImages from "../venue/FloorPlanImages";
import { canSwitchBoothZone, isBoothZoneLocked } from "./booking-zone-access";
import { INLINE_ERROR_REQUEST } from "./inline-error-request";

const signedPrice = (cents: number) =>
  `${cents < 0 ? "-" : "+"}${formatMoney(Math.abs(cents))}`;

type ZoneInclusions = Pick<
  BoothZoneWithAvailabilityResponse,
  "included_services"
>;

const zoneInclusion = (zone: ZoneInclusions, serviceId: string) =>
  zone.included_services.find((item) => item.service_id === serviceId)
    ?.included_quantity ?? 0;

const servicesNetInZone = (
  booking: BookingResponse,
  currentZone: ZoneInclusions,
  zone: ZoneInclusions,
) =>
  (booking.services ?? []).reduce((sum, item) => {
    const includedElsewhere = Math.max(
      item.included_quantity - zoneInclusion(currentZone, item.service_id),
      0,
    );
    const included = includedElsewhere + zoneInclusion(zone, item.service_id);
    return (
      sum + chargedServiceQuantity(item.quantity, included) * item.unit_price
    );
  }, 0);

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
  const {
    data: zones,
    isLoading: isLoadingZones,
    isError: isZonesError,
  } = useListAvailableBoothZones(event.id);
  const { data: waitlistEntries } = useListBookingUpgradeWaitlist(booking.id, {
    query: { enabled: canSwitch },
  });
  const { mutateAsync: switchZone } = useSwitchBookingZone({
    request: INLINE_ERROR_REQUEST,
  });
  const { mutateAsync: replaceWaitlist } = useReplaceBookingUpgradeWaitlist({
    request: INLINE_ERROR_REQUEST,
  });

  const currentZone = zones?.find((zone) => zone.id === booking.booth_zone_id);
  const currentBasePrice =
    currentZone?.base_price ?? booking.booth_zone?.base_price ?? 0;
  const currentInclusions: ZoneInclusions = currentZone ??
    booking.booth_zone ?? { included_services: [] };
  const currentServicesNet = servicesNetInZone(
    booking,
    currentInclusions,
    currentInclusions,
  );
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

  const showError = (error: unknown) =>
    setErrorCode(getApiErrorCode(error) ?? "server.error");

  const { run: submitSwitch, isRunning: isSwitching } = useAsyncAction(
    async (zone: BoothZoneWithAvailabilityResponse) => {
      setErrorCode(null);
      await switchZone({
        bookingId: booking.id,
        data: { booth_zone_id: zone.id },
      });
      await refreshBooking();
      notifySuccess(t("kp.zone_switch.switched", { zone: zone.name }));
      closeModal();
    },
    showError,
  );

  const { run: submitWaitlist, isRunning: isJoiningWaitlist } = useAsyncAction(
    async (zone: BoothZoneWithAvailabilityResponse) => {
      setErrorCode(null);
      const queryKey = getListBookingUpgradeWaitlistQueryKey(booking.id);
      const updated = await replaceWaitlist({
        bookingId: booking.id,
        data: { target_booth_zone_ids: [...waitlistedZoneIds, zone.id] },
      });
      queryClient.setQueryData(queryKey, updated);
      notifySuccess(t("kp.zone_switch.waitlist_added", { zone: zone.name }));
      closeModal();
      await queryClient.invalidateQueries({ queryKey });
    },
    showError,
  );

  const zoneDifference = (zone: BoothZoneWithAvailabilityResponse) => {
    const net =
      zone.base_price -
      currentBasePrice +
      servicesNetInZone(booking, currentInclusions, zone) -
      currentServicesNet;
    if (net === 0) return t("kp.zone_switch.price_same");
    return t("kp.zone_switch.price_difference", {
      net: signedPrice(net),
      gross: signedPrice(priceBreakdown(net, event.vat_rate_percent).gross),
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
              amount: formatMoney(currentBasePrice),
            })}
          </Text>
          <Text size="sm">
            {t("kp.zone_switch.price_gross", {
              amount: formatMoney(
                priceBreakdown(currentBasePrice, event.vat_rate_percent).gross,
              ),
            })}
          </Text>
          {currentZone ? (
            <Text size="sm" c={currentZone.is_full ? "red" : "green"}>
              {currentZone.is_full
                ? t("kp.zone_switch.zone_full")
                : t("kp.booth_size", { size: currentZone.booth_size })}
            </Text>
          ) : null}
        </Group>

        {canSwitch ? null : (
          <Text size="sm" c="dimmed">
            {t(
              isBoothZoneLocked(booking)
                ? "kp.zone_switch.disabled_confirmed"
                : "kp.zone_switch.disabled_deadline",
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
          <FloorPlanImages columns={2} />

          {errorCode ? (
            <Alert icon={<IconAlertCircle />} color="red">
              {t(errorCode)}
            </Alert>
          ) : null}

          {isZonesError ? (
            <ErrorAlert />
          ) : isLoadingZones ? (
            <PageLoader />
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
                  const isFull = zone.is_full;
                  const isSelected = zone.id === selectedZoneId;
                  return (
                    <UnstyledButton
                      key={zone.id}
                      aria-pressed={isSelected}
                      disabled={!zone.registration_open}
                      style={{ opacity: zone.registration_open ? 1 : 0.5 }}
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
                            {zone.registration_open ? null : (
                              <Badge color="gray" size="sm" variant="light">
                                {t("kp.booking.zone_closed")}
                              </Badge>
                            )}
                          </Group>
                          <Text size="xs" c={isFull ? "red" : "green"}>
                            {isFull
                              ? t("kp.zone_switch.zone_full")
                              : t("kp.booth_size", {
                                  size: zone.booth_size,
                                })}
                          </Text>
                        </Group>
                        <Group justify="space-between" mt={4} wrap="nowrap">
                          <Text size="xs" c="dimmed">
                            {t("kp.zone_switch.price_net", {
                              amount: formatMoney(zone.base_price),
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

          {selectedZone === null ? null : !selectedZone.is_full ? (
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
                disabled={
                  waitlistEntries === undefined ||
                  waitlistedZoneIds.includes(selectedZone.id)
                }
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
