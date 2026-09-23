import { Stack, Divider, Group, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import type { PriceBreakdown } from "../orval/generated/fastAPI.schemas";
import { formatPrice } from "../utils/price-utils";

type BookingSummaryServiceLine = { label: string; amount: number };

type BookingSummaryLineGroup = {
  title: string;
  lines: BookingSummaryServiceLine[];
};

const SummaryPriceBreakdown = ({
  additionalLines = [],
  groups,
  price,
  vatRatePercent,
}: {
  additionalLines?: BookingSummaryServiceLine[];
  groups?: BookingSummaryLineGroup[];
  price: PriceBreakdown;
  vatRatePercent?: number | null;
}) => {
  const { t } = useTranslation();
  const sections = groups ?? [
    {
      title: t("kp.booking.summary_additional_services"),
      lines: additionalLines,
    },
  ];
  const hasLines = sections.some((section) => section.lines.length > 0);

  return (
    <Stack gap="sm">
      <Divider />
      {hasLines ? (
        sections
          .filter((section) => section.lines.length > 0)
          .map((section) => (
            <Stack gap="sm" key={section.title}>
              <Text size="sm" fw={500}>
                {section.title}
              </Text>
              {section.lines.map((line) => (
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
              ))}
            </Stack>
          ))
      ) : (
        <>
          <Text size="sm" fw={500}>
            {t("kp.booking.summary_additional_services")}
          </Text>
          <Text size="sm" c="dimmed">
            {t("kp.booking.summary_no_additional_services")}
          </Text>
        </>
      )}
      <Divider />
      <Group justify="space-between" align="center" wrap="nowrap">
        <Text size="sm">{t("kp.booking.summary_net")}</Text>
        <Text size="sm" ta="right">
          CHF {formatPrice(price.net)}
        </Text>
      </Group>
      <Group justify="space-between" align="center" wrap="nowrap">
        <Text size="sm">
          {vatRatePercent == null
            ? t("kp.booking.summary_vat")
            : t("kp.booking.summary_vat_rate", { rate: vatRatePercent })}
        </Text>
        <Text size="sm" ta="right">
          CHF {formatPrice(price.vat)}
        </Text>
      </Group>
      <Group justify="space-between" align="center" wrap="nowrap">
        <Text size="sm" fw={600}>
          {t("kp.booking.summary_gross")}
        </Text>
        <Text size="sm" fw={600} ta="right">
          CHF {formatPrice(price.gross)}
        </Text>
      </Group>
    </Stack>
  );
};
export default SummaryPriceBreakdown;
