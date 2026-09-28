import { Card, Group, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { KpBookingStatusHelp } from "./KpBookingStatusHelp";
import { KpBookingStatusBadge } from "./KpBookingStatusBadge";
import type { BookingResponse } from "../orval/generated/fastAPI.schemas";
import { formatPrice } from "../utils/price-utils";
import type { BookingSummaryServiceLine } from "./KpBookingSummaryStep";
import SummaryPriceBreakdown from "./SummaryPriceBreakdown";
import { serviceLineLabel } from "../utils/kp-service-quantity";

function bookingToAdditionalServiceLines(
  booking: BookingResponse,
  t: (key: string, options?: Record<string, unknown>) => string,
): BookingSummaryServiceLine[] {
  return (booking.additional_service_charges ?? []).map((charge) => {
    const included = charge.quantity - charge.charged_quantity;
    return {
      label: serviceLineLabel(
        charge.name,
        charge.charged_quantity,
        included > 0
          ? t("kp.booking.service_included_note", { included })
          : null,
      ),
      amount: charge.line_net,
    };
  });
}

interface KpBookingRecapProps {
  booking: BookingResponse;
  vatRatePercent?: number | null;
}

export const KpBookingRecap = ({
  booking,
  vatRatePercent,
}: KpBookingRecapProps) => {
  const { t } = useTranslation();
  const additionalLines = bookingToAdditionalServiceLines(booking, t);
  const basePrice = booking.booth_zone?.base_price ?? 0;

  return (
    <Card
      withBorder
      radius="md"
      p="lg"
      m={0}
      style={{ boxShadow: "var(--visit-card-shadow)" }}
    >
      <Stack gap="sm">
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Text size="sm" fw={500}>
            {t("kp.booking.summary_zone")}
          </Text>
          <Text size="sm" ta="right">
            {booking.booth_zone?.name ?? booking.booth_zone_id}
          </Text>
        </Group>
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Text size="sm" fw={500}>
            {t("kp.booking.summary_booth_nr")}
          </Text>
          <Text size="sm" ta="right">
            {booking.booth_nr != null
              ? String(booking.booth_nr)
              : t("kp.booking.booth_nr_pending")}
          </Text>
        </Group>
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Text size="sm" fw={500}>
            {t("kp.booking.summary_price")}
          </Text>
          <Text size="sm" ta="right">
            CHF {formatPrice(basePrice)}
          </Text>
        </Group>
        <SummaryPriceBreakdown
          additionalLines={additionalLines}
          price={booking.price}
          vatRatePercent={vatRatePercent}
        />
        <Group justify="space-between" align="center" wrap="nowrap">
          <Text size="sm" fw={500}>
            {t("kp.booking.summary_status")}
          </Text>
          <Group gap={4} align="center" wrap="nowrap">
            <KpBookingStatusBadge status={booking.status} />
            <KpBookingStatusHelp />
          </Group>
        </Group>
      </Stack>
    </Card>
  );
};
export default KpBookingRecap;
