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
import { Fragment, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { KpBoothZoneColorSwatch } from "../components/KpBoothZoneColorSwatch";
import {
  KpBookingStatus,
  KpServiceCategory,
  type BookingServiceTotals,
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

const SERVICE_CATEGORY_LABEL_KEYS: Record<KpServiceCategory, string> = {
  [KpServiceCategory.SERVICE]: "kp.manage.services_group_services",
  [KpServiceCategory.BOOTH_ELEMENT]: "kp.manage.services_group_booth_elements",
};

const sumPrices = (services: BookingServiceTotals[]) =>
  services.reduce(
    (sum, service) => ({
      net: sum.net + service.price.net,
      gross: sum.gross + service.price.gross,
    }),
    { net: 0, gross: 0 },
  );

const ServiceRow = ({ service }: { service: BookingServiceTotals }) => {
  const { t } = useTranslation();
  const remaining = service.remaining_total_quantity;
  return (
    <Table.Tr>
      <Table.Td>
        <Text size="sm">{service.name}</Text>
        <Text size="xs" c="dimmed">
          {t("kp.bookings_overview.per_unit", {
            price: formatPrice(service.unit_price),
            unit: service.unit_label ?? t("kp.bookings_overview.unit"),
          })}
        </Text>
      </Table.Td>
      <Table.Td ta="right">
        <Text size="sm">{service.quantity}</Text>
        {service.included_quantity > 0 ? (
          <Text size="xs" c="dimmed">
            {t("kp.bookings_overview.included", {
              count: service.included_quantity,
            })}
          </Text>
        ) : null}
      </Table.Td>
      <Table.Td ta="right">{service.booking_count}</Table.Td>
      <Table.Td ta="right">
        {remaining === null ? (
          <Text size="sm" c="dimmed">
            {t("kp.bookings_overview.unlimited")}
          </Text>
        ) : (
          <Text size="sm" c={remaining === 0 ? "red" : undefined}>
            {`${remaining} / ${service.max_total_quantity}`}
          </Text>
        )}
      </Table.Td>
      <Table.Td ta="right">{formatPrice(service.price.net)}</Table.Td>
      <Table.Td ta="right">{formatPrice(service.price.gross)}</Table.Td>
    </Table.Tr>
  );
};

const ServiceTotalsTable = ({
  services,
}: {
  services: BookingServiceTotals[];
}) => {
  const { t } = useTranslation();
  const total = sumPrices(services);
  const categories = Object.values(KpServiceCategory)
    .map((category) => ({
      category,
      services: services.filter((service) => service.category === category),
    }))
    .filter((group) => group.services.length > 0);

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="sm">
        <Title order={4}>{t("kp.bookings_overview.by_service")}</Title>
        <Table.ScrollContainer minWidth={680}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th />
                <Table.Th ta="right">
                  {t("kp.bookings_overview.quantity")}
                </Table.Th>
                <Table.Th ta="right">
                  {t("kp.bookings_overview.bookings")}
                </Table.Th>
                <Table.Th ta="right">
                  {t("kp.bookings_overview.available")}
                </Table.Th>
                <Table.Th ta="right">{t("kp.bookings_overview.net")}</Table.Th>
                <Table.Th ta="right">
                  {t("kp.bookings_overview.gross")}
                </Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {categories.map((group) => (
                <Fragment key={group.category}>
                  <Table.Tr>
                    <Table.Th colSpan={6}>
                      <Text size="xs" c="dimmed" fw={600} tt="uppercase">
                        {t(SERVICE_CATEGORY_LABEL_KEYS[group.category])}
                      </Text>
                    </Table.Th>
                  </Table.Tr>
                  {group.services.map((service) => (
                    <ServiceRow key={service.service_id} service={service} />
                  ))}
                </Fragment>
              ))}
            </Table.Tbody>
            <Table.Tfoot>
              <Table.Tr>
                <Table.Td colSpan={4}>
                  <Text size="sm" fw={600}>
                    {t("kp.bookings_overview.services_total")}
                  </Text>
                </Table.Td>
                <Table.Td ta="right">{formatPrice(total.net)}</Table.Td>
                <Table.Td ta="right">{formatPrice(total.gross)}</Table.Td>
              </Table.Tr>
            </Table.Tfoot>
          </Table>
        </Table.ScrollContainer>
        <Text size="xs" c="dimmed">
          {t("kp.bookings_overview.services_note")}
        </Text>
      </Stack>
    </Paper>
  );
};

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

          {summary.by_service.length > 0 ? (
            <ServiceTotalsTable services={summary.by_service} />
          ) : null}
        </>
      )}
    </Stack>
  );
};

export default BookingsOverview;
