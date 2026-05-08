import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Group,
  Loader,
  SimpleGrid,
  Stack,
  Stepper,
  Text,
  Title,
} from "@mantine/core";
import {
  IconAlertCircle,
  IconCalendarEvent,
  IconCalendarTime,
  IconCheck,
  IconTicket,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import { KpBoothZoneColorSwatch } from "../components/KpBoothZoneColorSwatch";
import { KpBookingStatusHelp } from "../components/KpBookingStatusHelp";
import { KpBookingStatusBadge } from "../components/KpBookingStatusBadge";
import { useGetKpById, useGetMyBooking } from "../orval/generated/kp/kp";
import {
  EVENT_STATUS_COLORS,
  formatKpDisplayDate,
  getEventStatus,
} from "../utils/kp-utils";
import { formatPrice } from "../utils/price-utils";

const KpCompanyView = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id = "" } = useParams<{ id: string }>();
  const eventId = id.trim();

  const {
    data: event,
    isLoading,
    isError,
  } = useGetKpById(eventId, {
    query: { enabled: Boolean(eventId) },
  });

  const status = event ? getEventStatus(event) : null;
  const isRegistrationOpen = status === "registration_open";

  const { data: myBooking, isLoading: isLoadingBooking } = useGetMyBooking(
    eventId,
    { query: { enabled: !!eventId } },
  );

  const timelineActiveStep = event
    ? [
        event.registration_open,
        event.registration_end,
        event.finalization_deadline,
        event.nametags_deadline,
        event.event_date,
      ].filter((isoDate) => new Date(isoDate).getTime() <= Date.now()).length
    : 0;

  return (
    <Stack gap="md">
      <BackButton to="/" />

      <Group justify="space-between" align="center">
        <div>
          <Title order={2}>{t("kp.company_view.title")}</Title>
          <Text c="dimmed" size="sm">
            {t("kp.company_view.subtitle")}
          </Text>
        </div>
      </Group>

      {isLoading ? (
        <Center py="xl">
          <Loader />
        </Center>
      ) : null}

      {isError && !isLoading ? (
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.company_view.error")}
        </Alert>
      ) : null}

      {!isLoading && !isError && !event ? (
        <Card withBorder radius="md" p="lg">
          <Text c="dimmed" ta="center">
            {t("kp.company_view.no_event")}
          </Text>
        </Card>
      ) : null}

      {!isLoading && !isError && event && status ? (
        <Stack gap="md">
          <Card withBorder radius="md" p="lg">
            <Group justify="space-between" align="center" mb="md">
              <Group gap="sm">
                <IconCalendarEvent size={24} />
                <Title order={3}>{event.name}</Title>
              </Group>
              <Badge
                color={EVENT_STATUS_COLORS[status]}
                variant="light"
                size="sm"
              >
                {t(`kp.company_view.status_${status}`)}
              </Badge>
            </Group>

            <Stack gap="xs" mt="md">
              <Text size="sm" c="dimmed">
                {t("kp.company_view.event_timeline")}
              </Text>
              <Stepper
                active={timelineActiveStep}
                iconSize={34}
                size="xs"
                allowNextStepsSelect={false}
                orientation="horizontal"
              >
                <Stepper.Step
                  label={t("kp.company_view.registration_open")}
                  description={
                    <Text size="sm" fw={600}>
                      {formatKpDisplayDate(event.registration_open)}
                    </Text>
                  }
                  icon={<IconCalendarTime size={18} />}
                />
                <Stepper.Step
                  label={t("kp.company_view.registration_end")}
                  description={
                    <Text size="sm" fw={600}>
                      {formatKpDisplayDate(event.registration_end)}
                    </Text>
                  }
                  icon={<IconCalendarTime size={18} />}
                />
                <Stepper.Step
                  label={t("kp.company_view.finalization_deadline")}
                  description={
                    <Text size="sm" fw={600}>
                      {formatKpDisplayDate(event.finalization_deadline)}
                    </Text>
                  }
                  icon={<IconCalendarTime size={18} />}
                />
                <Stepper.Step
                  label={t("kp.company_view.nametags_deadline")}
                  description={
                    <Text size="sm" fw={600}>
                      {formatKpDisplayDate(event.nametags_deadline)}
                    </Text>
                  }
                  icon={<IconCalendarTime size={18} />}
                />
                <Stepper.Step
                  label={t("kp.company_view.event_date")}
                  description={
                    <Text size="sm" fw={600}>
                      {formatKpDisplayDate(event.event_date)}
                    </Text>
                  }
                  icon={<IconCalendarEvent size={18} />}
                />
              </Stepper>
            </Stack>
          </Card>

          {/* Booking section */}
          {isLoadingBooking ? (
            <Center py="md">
              <Loader />
            </Center>
          ) : myBooking ? (
            <Card withBorder radius="md" p="lg">
              <Group justify="space-between" align="center" mb="md">
                <Group gap="sm">
                  <IconCheck size={20} />
                  <Title order={4}>
                    {t("kp.company_view.booking_title", {
                      bookingNumber: myBooking.booking_number,
                    })}
                  </Title>
                </Group>
              </Group>
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                <div>
                  <Text size="sm" c="dimmed">
                    {t("kp.company_view.booking_zone")}
                  </Text>
                  {myBooking.booth_zone ? (
                    <Group gap="xs" align="center">
                      <KpBoothZoneColorSwatch
                        color={myBooking.booth_zone.color}
                      />
                      <Text fw={500}>{myBooking.booth_zone.name}</Text>
                    </Group>
                  ) : (
                    <Text fw={500}>{myBooking.booth_zone_id}</Text>
                  )}
                </div>
                <div>
                  <Text size="sm" c="dimmed">
                    {t("kp.company_view.booking_booth_nr")}
                  </Text>
                  <Text fw={500}>
                    {myBooking.booth_nr != null
                      ? String(myBooking.booth_nr)
                      : t("kp.booking.booth_nr_pending")}
                  </Text>
                </div>
                <div>
                  <Text size="sm" c="dimmed">
                    {t("kp.company_view.booking_price")}
                  </Text>
                  <Text fw={500}>
                    CHF {formatPrice(myBooking.booth_zone?.base_price ?? 0)}
                  </Text>
                </div>
                <div>
                  <Group gap={6} align="center">
                    <Text size="sm" c="dimmed" style={{ lineHeight: 1 }}>
                      {t("kp.company_view.booking_status")}
                    </Text>
                    <KpBookingStatusHelp />
                  </Group>
                  <KpBookingStatusBadge status={myBooking.status} size="md" />
                </div>
              </SimpleGrid>
              <Button
                mt="md"
                variant="light"
                leftSection={<IconTicket size={18} />}
                onClick={() =>
                  navigate(`/kp/${eventId}/booking/${myBooking.id}`)
                }
              >
                {t("kp.company_view.manage_booking")}
              </Button>
            </Card>
          ) : isRegistrationOpen ? (
            <Card withBorder radius="md" p="lg" ta="center">
              <Stack align="center" gap="md">
                <IconTicket size={48} style={{ opacity: 0.5 }} />
                <div>
                  <Title order={4}>
                    {t("kp.company_view.no_booking_title")}
                  </Title>
                  <Text c="dimmed" size="sm" mt="xs">
                    {t("kp.company_view.no_booking_description")}
                  </Text>
                </div>
                <Button
                  size="md"
                  leftSection={<IconTicket size={18} />}
                  onClick={() => navigate(`/kp/${eventId}/booking`)}
                >
                  {t("kp.company_view.start_booking")}
                </Button>
              </Stack>
            </Card>
          ) : (
            <Alert icon={<IconAlertCircle />} color="yellow">
              {t("kp.company_view.registration_closed")}
            </Alert>
          )}
        </Stack>
      ) : null}
    </Stack>
  );
};
export default KpCompanyView;
