import { Card, Group, Text, UnstyledButton } from "@mantine/core";
import { IconCheck } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { BoothZoneWithAvailabilityResponse } from "../orval/generated/fastAPI.schemas";
import { formatPrice } from "../utils/price-utils";

interface KpBookingZoneCardProps {
  zone: BoothZoneWithAvailabilityResponse;
  isSelected: boolean;
  isDisabled: boolean;
  onSelect: () => void;
}

const KpBookingZoneCard = ({
  zone,
  isSelected,
  isDisabled,
  onSelect,
}: KpBookingZoneCardProps) => {
  const { t } = useTranslation();
  const isFull = zone.available_spots <= 0;

  return (
    <UnstyledButton
      onClick={onSelect}
      disabled={isDisabled}
      style={{ opacity: isDisabled ? 0.5 : 1 }}
    >
      <Card
        withBorder
        radius="md"
        p="md"
        style={{
          borderColor: isSelected ? "var(--mantine-color-blue-5)" : undefined,
          borderWidth: isSelected ? 2 : 1,
          cursor: isDisabled ? "not-allowed" : "pointer",
        }}
      >
        <Group justify="space-between" align="flex-start">
          <Group gap="xs">
            <div
              style={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                backgroundColor: zone.color,
                flexShrink: 0,
                marginTop: 4,
              }}
            />
            <div>
              <Text fw={600} size="sm">
                {zone.name}
              </Text>
              {isSelected && zone.description ? (
                <Text size="xs" c="dimmed" mt={2}>
                  {zone.description}
                </Text>
              ) : null}
            </div>
          </Group>
          {isSelected ? (
            <IconCheck size={18} color="var(--mantine-color-blue-5)" />
          ) : null}
        </Group>

        <Group justify="space-between" mt="xs">
          <Text size="xs" fw={500} c={isFull ? "red" : "green"}>
            {isFull
              ? t("kp.booking.zone_full")
              : t("kp.booking.zone_available", {
                  available: zone.available_spots,
                  total: zone.capacity,
                })}
          </Text>
          <Text size="xs" c="dimmed">
            CHF {formatPrice(zone.base_price)}
          </Text>
        </Group>
      </Card>
    </UnstyledButton>
  );
};
export default KpBookingZoneCard;
