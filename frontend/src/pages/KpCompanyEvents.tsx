import {
  Alert,
  Badge,
  Card,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconCalendarEvent } from "@tabler/icons-react";
import { useQueries } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import BackButton from "../components/BackButton";
import {
  getGetMyBookingQueryKey,
  getMyBooking,
  useListKps,
} from "../orval/generated/kp/kp";
import {
  EVENT_STATUS_COLORS,
  formatKpDisplayDate,
  getEventStatus,
} from "../utils/kp-utils";

export default function KpCompanyEvents() {
  const { t } = useTranslation();
  const { data: events, isLoading, isError } = useListKps();
  const bookingQueries = useQueries({
    queries: (events ?? []).map((event) => ({
      queryKey: getGetMyBookingQueryKey(event.id),
      queryFn: ({ signal }: { signal: AbortSignal }) =>
        getMyBooking(event.id, undefined, signal),
      enabled: Boolean(event.id),
      retry: false,
    })),
  });

  const isLoadingBookings = bookingQueries.some(
    (q) => q.isLoading || q.isFetching,
  );
  const bookedEventIds = new Set(
    bookingQueries
      .map((q) => q.data?.event_id)
      .filter((value): value is string => Boolean(value)),
  );

  const allEvents = events ?? [];
  const currentlyOpenEvents = allEvents.filter(
    (event) => getEventStatus(event) === "registration_open",
  );
  const participatedPastEvents = allEvents.filter(
    (event) => getEventStatus(event) === "past" && bookedEventIds.has(event.id),
  );
  const hasAnyDisplayedEvents =
    currentlyOpenEvents.length > 0 || participatedPastEvents.length > 0;

  if (isLoading || (Boolean(events?.length) && isLoadingBookings)) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (isError) {
    return (
      <Stack gap="md">
        <BackButton to="/" />
        <Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
          {t("kp.company_view.error")}
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <BackButton to="/" />
      <div>
        <Title order={2}>{t("kp.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("kp.history.title")}
        </Text>
      </div>

      {currentlyOpenEvents.length ? (
        <Stack gap="sm">
          <Text fw={600}>{t("kp.join.current_event")}</Text>
          {currentlyOpenEvents.map((event) => (
            <Card
              key={event.id}
              component={Link}
              to={`/kp/${event.id}`}
              withBorder
              radius="md"
              p="lg"
            >
              <Group justify="space-between" align="center" mb="xs">
                <Group gap="sm">
                  <IconCalendarEvent size={20} />
                  <Text fw={600}>{event.name}</Text>
                </Group>
                <Badge
                  color={EVENT_STATUS_COLORS.registration_open}
                  variant="light"
                  size="sm"
                >
                  {t("kp.company_view.status_registration_open")}
                </Badge>
              </Group>
              <Text size="sm" c="dimmed">
                {t("kp.company_view.event_date")}:{" "}
                {formatKpDisplayDate(event.event_date)}
              </Text>
            </Card>
          ))}
        </Stack>
      ) : null}

      {!hasAnyDisplayedEvents ? (
        <Card withBorder radius="md" p="lg">
          <Text c="dimmed" ta="center">
            {t("kp.history.none")}
          </Text>
        </Card>
      ) : participatedPastEvents.length ? (
        <Stack gap="sm">
          <Text fw={600}>{t("kp.history.title")}</Text>
          {participatedPastEvents.map((event) => {
            const status = getEventStatus(event);
            return (
              <Card
                key={event.id}
                component={Link}
                to={`/kp/${event.id}`}
                withBorder
                radius="md"
                p="lg"
              >
                <Group justify="space-between" align="center" mb="xs">
                  <Group gap="sm">
                    <IconCalendarEvent size={20} />
                    <Text fw={600}>{event.name}</Text>
                  </Group>
                  <Badge
                    color={EVENT_STATUS_COLORS[status]}
                    variant="light"
                    size="sm"
                  >
                    {t(`kp.company_view.status_${status}`)}
                  </Badge>
                </Group>
                <Text size="sm" c="dimmed">
                  {t("kp.company_view.event_date")}:{" "}
                  {formatKpDisplayDate(event.event_date)}
                </Text>
              </Card>
            );
          })}
        </Stack>
      ) : null}
    </Stack>
  );
}
