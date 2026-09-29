import {
  Alert,
  Center,
  Group,
  Loader,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { KpBoothZoneColorSwatch } from "../components/KpBoothZoneColorSwatch";
import {
  KpBookingStatus,
  type BookingTotals,
} from "../orval/generated/fastAPI.schemas";
import { useGetBookingsSummary, useListKps } from "../orval/generated/kp/kp";
import { BOOKING_STATUS_LABEL_KEYS } from "../utils/kp-utils";
import { formatPrice } from "../utils/price-utils";

interface Occupancy {
  occupied: number;
  capacity: number;
  free: number;
}

const TotalsRow = ({
  label,
  totals,
  occupancy,
  dimmed = false,
}: {
  label: ReactNode;
  totals: BookingTotals;
  occupancy?: Occupancy;
  dimmed?: boolean;
}) => (
  <Table.Tr c={dimmed ? "dimmed" : undefined}>
    <Table.Td>{label}</Table.Td>
    <Table.Td ta="right">
      {occupancy ? (
        <Text
          size="sm"
          c={occupancy.occupied > occupancy.capacity ? "red" : undefined}
        >
          {`${occupancy.occupied} / ${occupancy.capacity}`}
        </Text>
      ) : (
        totals.count
      )}
    </Table.Td>
    <Table.Td ta="right">{occupancy?.free}</Table.Td>
    <Table.Td ta="right">{formatPrice(totals.base)}</Table.Td>
    <Table.Td ta="right">{formatPrice(totals.services)}</Table.Td>
    <Table.Td ta="right">{formatPrice(totals.price.net)}</Table.Td>
    <Table.Td ta="right">{formatPrice(totals.price.gross)}</Table.Td>
  </Table.Tr>
);

const BookingsOverview = () => {
  const { t } = useTranslation();
  const { data: events, isLoading: isLoadingEvents } = useListKps();
  const [pickedEventId, setPickedEventId] = useState<string | null>(null);
  const eventId = pickedEventId ?? events?.at(0)?.id ?? "";
  const { data: summary, isLoading: isLoadingSummary } = useGetBookingsSummary(
    eventId,
    { query: { enabled: Boolean(eventId) } },
  );

  const sectionRow = (label: string) => (
    <Table.Tr>
      <Table.Th colSpan={7}>
        <Text size="xs" c="dimmed" fw={600} tt="uppercase">
          {label}
        </Text>
      </Table.Th>
    </Table.Tr>
  );

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <Title order={2}>{t("kp.bookings_overview.title")}</Title>
        <Select
          label={t("kp.bookings_overview.event")}
          data={(events ?? []).map((event) => ({
            value: event.id,
            label: event.name,
          }))}
          value={eventId || null}
          onChange={setPickedEventId}
          allowDeselect={false}
          disabled={isLoadingEvents}
          w={{ base: "100%", sm: 280 }}
        />
      </Group>

      {isLoadingEvents || isLoadingSummary ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : !summary ? (
        <Alert icon={<IconAlertCircle />} color="gray">
          {t("kp.bookings_overview.empty")}
        </Alert>
      ) : (
        <>
          <Paper withBorder p="lg" radius="md">
            <Stack gap={4}>
              <Text size="sm" c="dimmed">
                {t("kp.bookings_overview.total")}
              </Text>
              <Title order={1}>
                {`CHF ${formatPrice(summary.total.price.gross)}`}
              </Title>
              <Text size="sm" c="dimmed">
                {t("kp.bookings_overview.total_detail", {
                  net: formatPrice(summary.total.price.net),
                  vat: formatPrice(summary.total.price.vat),
                  rate: summary.vat_rate_percent,
                })}
              </Text>
            </Stack>
          </Paper>

          <Paper withBorder p="lg" radius="md">
            <Stack gap="sm">
              <Table.ScrollContainer minWidth={680}>
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th />
                      <Table.Th ta="right">
                        {t("kp.bookings_overview.bookings")}
                      </Table.Th>
                      <Table.Th ta="right">
                        {t("kp.bookings_overview.free")}
                      </Table.Th>
                      <Table.Th ta="right">
                        {t("kp.bookings_overview.base")}
                      </Table.Th>
                      <Table.Th ta="right">
                        {t("kp.bookings_overview.services")}
                      </Table.Th>
                      <Table.Th ta="right">
                        {t("kp.bookings_overview.net")}
                      </Table.Th>
                      <Table.Th ta="right">
                        {t("kp.bookings_overview.gross")}
                      </Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {sectionRow(t("kp.bookings_overview.by_status"))}
                    {summary.by_status.map((entry) => (
                      <TotalsRow
                        key={entry.status}
                        label={t(BOOKING_STATUS_LABEL_KEYS[entry.status])}
                        totals={entry}
                      />
                    ))}
                    {summary.offered.count > 0 ? (
                      <TotalsRow
                        label={t(
                          BOOKING_STATUS_LABEL_KEYS[KpBookingStatus.OFFERED],
                        )}
                        totals={summary.offered}
                        dimmed
                      />
                    ) : null}
                    {sectionRow(t("kp.bookings_overview.by_zone"))}
                    {summary.by_zone.map((zone) => (
                      <TotalsRow
                        key={zone.booth_zone_id}
                        label={
                          <Group gap="xs" wrap="nowrap">
                            <KpBoothZoneColorSwatch color={zone.color} />
                            <div>
                              <Text size="sm">{zone.name}</Text>
                              <Text size="xs" c="dimmed">
                                {t("kp.bookings_overview.per_booth", {
                                  price: formatPrice(zone.base_price),
                                })}
                              </Text>
                            </div>
                          </Group>
                        }
                        totals={zone}
                        occupancy={zone}
                      />
                    ))}
                  </Table.Tbody>
                  <Table.Tfoot>
                    <TotalsRow
                      label={
                        <Text size="sm" fw={600}>
                          {t("kp.bookings_overview.all")}
                        </Text>
                      }
                      totals={summary.total}
                      occupancy={summary}
                    />
                  </Table.Tfoot>
                </Table>
              </Table.ScrollContainer>
              <Text size="xs" c="dimmed">
                {t("kp.bookings_overview.excluded", {
                  cancelled: summary.cancelled_count,
                  rejected: summary.rejected_count,
                  expired: summary.expired_count,
                })}
              </Text>
            </Stack>
          </Paper>
        </>
      )}
    </Stack>
  );
};

export default BookingsOverview;
