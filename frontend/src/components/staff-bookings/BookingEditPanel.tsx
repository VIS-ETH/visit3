import {
  Alert,
  Button,
  Group,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type {
  StaffBookingResponse,
  StaffUpdateBookingRequest,
} from "../../orval/generated/fastAPI.schemas";
import {
  useListBoothZones,
  useListEventBookings,
  useListServices,
} from "../../orval/generated/kp/kp";
import { isActiveBookingStatus } from "../../utils/booking-status";
import {
  bookingEditFieldErrors,
  type BookingEditFieldErrors,
} from "./booking-errors";
import { useBookingActions } from "./useBookingActions";
import { formatMoney } from "../../utils/money";
import { useAsyncAction } from "../../hooks/use-async-action";

const bookedQuantities = (booking: StaffBookingResponse) =>
  Object.fromEntries(
    (booking.services ?? []).map((bookingService) => [
      bookingService.service_id,
      bookingService.quantity,
    ]),
  );

const BookingEditPanel = ({
  booking,
  eventId,
}: {
  booking: StaffBookingResponse;
  eventId: string;
}) => {
  const { t } = useTranslation();
  const actions = useBookingActions(eventId);
  const { data: zones } = useListBoothZones(eventId);
  const { data: services } = useListServices(eventId);
  const { data: bookings } = useListEventBookings(eventId);

  const [boothZoneId, setBoothZoneId] = useState(booking.booth_zone_id);
  const [boothNr, setBoothNr] = useState<string | number>(
    booking.booth_nr ?? "",
  );
  const [statusNote, setStatusNote] = useState(booking.status_note ?? "");
  const [quantities, setQuantities] = useState<Record<string, number>>(
    bookedQuantities(booking),
  );
  const [addedServiceIds, setAddedServiceIds] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<BookingEditFieldErrors>({});

  const originalQuantities = bookedQuantities(booking);
  const bookedServiceIds = Object.keys(originalQuantities);
  const rowServiceIds = [...new Set([...bookedServiceIds, ...addedServiceIds])];
  const servicesById = new Map(
    (services ?? []).map((service) => [service.id, service]),
  );

  const usedSpotsByZone = (bookings ?? []).reduce<Record<string, number>>(
    (counts, other) => {
      if (!isActiveBookingStatus(other.status)) return counts;
      counts[other.booth_zone_id] = (counts[other.booth_zone_id] ?? 0) + 1;
      return counts;
    },
    {},
  );

  const zoneOptions = (zones ?? []).map((zone) => ({
    value: zone.id,
    label: zone.name,
  }));

  const zoneAvailability = (zoneId: string) => {
    const zone = (zones ?? []).find((candidate) => candidate.id === zoneId);
    if (!zone) return undefined;
    return t("kp.manage.booking_edit_zone_availability", {
      available: Math.max(0, zone.capacity - (usedSpotsByZone[zone.id] ?? 0)),
      capacity: zone.capacity,
    });
  };

  const addableServiceOptions = (services ?? [])
    .filter(
      (service) => service.is_active && !rowServiceIds.includes(service.id),
    )
    .map((service) => ({ value: service.id, label: service.name }));

  const serviceName = (serviceId: string) =>
    servicesById.get(serviceId)?.name ??
    (booking.services ?? []).find(
      (bookingService) => bookingService.service_id === serviceId,
    )?.service.name ??
    serviceId;

  const unitPrice = (serviceId: string) =>
    (booking.services ?? []).find(
      (bookingService) => bookingService.service_id === serviceId,
    )?.unit_price ??
    servicesById.get(serviceId)?.price ??
    0;

  const changedPayload = (): StaffUpdateBookingRequest => {
    const payload: StaffUpdateBookingRequest = {};
    if (boothZoneId !== booking.booth_zone_id) {
      payload.booth_zone_id = boothZoneId;
    }
    const nextBoothNr = boothNr === "" ? null : Number(boothNr);
    if (nextBoothNr !== booking.booth_nr) payload.booth_nr = nextBoothNr;
    if (statusNote !== (booking.status_note ?? "")) {
      payload.status_note = statusNote;
    }
    const changedServices = rowServiceIds
      .filter(
        (serviceId) =>
          (quantities[serviceId] ?? 0) !== (originalQuantities[serviceId] ?? 0),
      )
      .map((serviceId) => ({
        service_id: serviceId,
        quantity: quantities[serviceId] ?? 0,
      }));
    if (changedServices.length > 0) payload.services = changedServices;
    return payload;
  };

  const resetTo = (source: StaffBookingResponse) => {
    setBoothZoneId(source.booth_zone_id);
    setBoothNr(source.booth_nr ?? "");
    setStatusNote(source.status_note ?? "");
    setQuantities(bookedQuantities(source));
    setAddedServiceIds([]);
    setFieldErrors({});
  };

  const { run: save, isRunning: isSaving } = useAsyncAction(
    async () => {
      const payload = changedPayload();
      if (Object.keys(payload).length === 0) {
        notifications.show({
          color: "blue",
          message: t("kp.manage.booking_edit_no_changes"),
        });
        return;
      }
      setFieldErrors({});
      resetTo(await actions.updateBooking(booking.id, payload));
    },
    (error) => setFieldErrors(bookingEditFieldErrors(error)),
  );

  return (
    <Paper withBorder p="lg" radius="md">
      <Stack gap="lg">
        <Title order={4}>{t("kp.manage.booking_edit_title")}</Title>

        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <Select
            allowDeselect={false}
            data={zoneOptions}
            disabled={isSaving}
            error={fieldErrors.zone ? t(fieldErrors.zone) : undefined}
            label={t("kp.manage.booking_edit_zone")}
            onChange={(value) => setBoothZoneId(value ?? boothZoneId)}
            renderOption={({ option }) => (
              <Group justify="space-between" w="100%">
                <Text size="sm">{option.label}</Text>
                <Text c="dimmed" size="xs">
                  {zoneAvailability(option.value)}
                </Text>
              </Group>
            )}
            searchable
            value={boothZoneId}
          />
          <NumberInput
            allowDecimal={false}
            disabled={isSaving}
            error={fieldErrors.boothNr ? t(fieldErrors.boothNr) : undefined}
            label={t("kp.manage.booking_edit_booth_nr")}
            min={1}
            onChange={setBoothNr}
            value={boothNr}
          />
        </SimpleGrid>

        <Stack gap="sm">
          <Text fw={600} size="sm">
            {t("kp.manage.booking_edit_services")}
          </Text>
          {fieldErrors.services ? (
            <Alert color="red" icon={<IconAlertCircle />}>
              {t(fieldErrors.services)}
            </Alert>
          ) : null}
          {rowServiceIds.length > 0 ? (
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>
                    {t("kp.manage.booking_edit_service_name")}
                  </Table.Th>
                  <Table.Th>
                    {t("kp.manage.booking_edit_service_unit_price")}
                  </Table.Th>
                  <Table.Th w={140}>
                    {t("kp.manage.booking_edit_service_quantity")}
                  </Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rowServiceIds.map((serviceId) => (
                  <Table.Tr key={serviceId}>
                    <Table.Td>{serviceName(serviceId)}</Table.Td>
                    <Table.Td>{formatMoney(unitPrice(serviceId))}</Table.Td>
                    <Table.Td>
                      <NumberInput
                        allowDecimal={false}
                        aria-label={serviceName(serviceId)}
                        disabled={isSaving}
                        max={999}
                        min={0}
                        onChange={(value) =>
                          setQuantities((previous) => ({
                            ...previous,
                            [serviceId]: Number(value) || 0,
                          }))
                        }
                        size="xs"
                        value={quantities[serviceId] ?? 0}
                      />
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Text c="dimmed" size="sm">
              {t("kp.manage.booking_services_empty")}
            </Text>
          )}
          <Select
            data={addableServiceOptions}
            disabled={isSaving}
            label={t("kp.manage.booking_edit_add_service")}
            onChange={(value) => {
              if (!value) return;
              setAddedServiceIds((previous) => [...previous, value]);
              setQuantities((previous) => ({ ...previous, [value]: 1 }));
            }}
            placeholder={t("kp.manage.booking_edit_add_service_placeholder")}
            searchable
            value={null}
          />
        </Stack>

        <Textarea
          autosize
          disabled={isSaving}
          label={t("kp.manage.booking_edit_status_note")}
          minRows={3}
          onChange={(event) => setStatusNote(event.currentTarget.value)}
          value={statusNote}
        />

        <Group justify="flex-end">
          <Button
            disabled={isSaving}
            onClick={() => resetTo(booking)}
            variant="subtle"
          >
            {t("kp.manage.booking_edit_reset")}
          </Button>
          <Button
            loading={isSaving}
            onClick={() => {
              void save();
            }}
          >
            {t("kp.manage.booking_edit_save")}
          </Button>
        </Group>
      </Stack>
    </Paper>
  );
};

export default BookingEditPanel;
