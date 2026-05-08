import { Stack, Divider, Group, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { formatPrice } from "../utils/price-utils";

type BookingSummaryServiceLine = { label: string; amount: number };

const SummaryPriceBreakdown = ({
  basePrice,
  additionalLines,
}: {
  basePrice: number;
  additionalLines: BookingSummaryServiceLine[];
}) => {
  const { t } = useTranslation();
  const servicesSubtotal = additionalLines.reduce(
    (s, line) => s + line.amount,
    0,
  );
  const total = basePrice + servicesSubtotal;

  return (
    <Stack gap="sm">
      <Divider />
      <Text size="sm" fw={500}>
        {t("kp.booking.summary_additional_services")}
      </Text>
      {additionalLines.length === 0 ? (
        <Text size="sm" c="dimmed">
          {t("kp.booking.summary_no_additional_services")}
        </Text>
      ) : (
        additionalLines.map((line) => (
          <Group
            key={`${line.label}-${line.amount}`}
            justify="space-between"
            align="flex-start"
            wrap="nowrap"
          >
            <Text size="sm">{line.label}</Text>
            <Text size="sm" ta="right">
              CHF {formatPrice(line.amount)}
            </Text>
          </Group>
        ))
      )}
      <Divider />
      <Group justify="space-between" align="center" wrap="nowrap">
        <Text size="sm" fw={600}>
          {t("kp.booking.summary_total")}
        </Text>
        <Text size="sm" fw={600} ta="right">
          CHF {formatPrice(total)}
        </Text>
      </Group>
    </Stack>
  );
};
export default SummaryPriceBreakdown;
