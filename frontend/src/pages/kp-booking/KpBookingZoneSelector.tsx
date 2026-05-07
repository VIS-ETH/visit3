import {
  Alert,
  Center,
  Loader,
  Paper,
  ScrollArea,
  Stack,
  Text,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
} from "../../orval/generated/fastAPI.schemas";
import { useListAvailableBoothZones } from "../../orval/generated/kp/kp";
import KpBookingZoneCard from "./KpBookingZoneCard";

interface KpBookingZoneSelectorProps {
  eventId: string;
  currentBooking: BookingResponse | null | undefined;
  selectedZone: BoothZoneWithAvailabilityResponse | null;
  onSelectZone: (zone: BoothZoneWithAvailabilityResponse) => void;
}

export default function KpBookingZoneSelector({
  eventId,
  currentBooking,
  selectedZone,
  onSelectZone,
}: KpBookingZoneSelectorProps) {
  const { t } = useTranslation();
  const { data: availableZones, isLoading: isLoadingZones } =
    useListAvailableBoothZones(eventId);
  const isZoneLocked = Boolean(currentBooking);

  useEffect(() => {
    if (!currentBooking || !availableZones) return;
    const bookedZone = availableZones.find(
      (zone) => zone.id === currentBooking.booth_zone_id,
    );
    if (bookedZone) {
      onSelectZone(bookedZone);
    }
  }, [availableZones, currentBooking, onSelectZone]);

  return (
    <Stack gap="sm">
      {isZoneLocked ? (
        <Alert icon={<IconAlertCircle />} color="yellow">
          {t("kp.booking.zone_locked")}
        </Alert>
      ) : null}
      <Paper withBorder radius="md" p="md" style={{ minHeight: 400 }}>
        {isLoadingZones ? (
          <Center h="100%">
            <Loader />
          </Center>
        ) : (
          <ScrollArea h={368} type="auto" scrollbarSize={6} offsetScrollbars>
            <Stack gap="sm" pr={8}>
              {availableZones?.map((zone) => {
                const isSelected = selectedZone?.id === zone.id;
                const isFull = zone.available_spots <= 0;
                const isDisabled = isZoneLocked ? !isSelected : isFull;

                return (
                  <KpBookingZoneCard
                    key={zone.id}
                    zone={zone}
                    isSelected={isSelected}
                    isDisabled={isDisabled}
                    onSelect={() => onSelectZone(zone)}
                  />
                );
              })}
            </Stack>
          </ScrollArea>
        )}
      </Paper>
      {!availableZones?.length && !isLoadingZones ? (
        <Text c="dimmed" size="sm">
          {t("kp.booking.zone_no_spots")}
        </Text>
      ) : null}
    </Stack>
  );
}
