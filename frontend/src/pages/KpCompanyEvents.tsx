import { Badge, Card, Group, Stack, Text, Title } from "@mantine/core";
import { IconCalendarEvent } from "@tabler/icons-react";
import { useQueries } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import BackButton from "../components/BackButton";
import ErrorAlert from "../components/ErrorAlert";
import PageLoader from "../components/PageLoader";
import type { KpResponse } from "../orval/generated/fastAPI.schemas";
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
import { activeBooking } from "../utils/my-booking";

const EventCard = ({ event }: { event: KpResponse }) => {
  const { t } = useTranslation();
  const status = getEventStatus(event);
  return (
    <Card component={Link} to={`/kp/${event.id}`} withBorder radius="md" p="lg">
      <Group justify="space-between" align="center" mb="xs">
        <Group gap="sm">
          <IconCalendarEvent size={20} />
          <Text fw={600}>{event.name}</Text>
        </Group>
        <Badge color={EVENT_STATUS_COLORS[status]} variant="light" size="sm">
          {t(`kp.company_view.status_${status}`)}
        </Badge>
      </Group>
      <Text size="sm" c="dimmed">
        {t("kp.company_view.event_date")}:{" "}
        {formatKpDisplayDate(event.event_date)}
      </Text>
    </Card>
  );
};

const KpCompanyEvents = () => {
  const { t } = useTranslation();
  const { data: events, isPending, isError } = useListKps();
  const bookingQueries = useQueries({
    queries: (events ?? []).map((event) => ({
      queryKey: getGetMyBookingQueryKey(event.id),
      queryFn: ({ signal }: { signal: AbortSignal }) =>
        getMyBooking(event.id, undefined, signal),
      enabled: Boolean(event.id),
      retry: false,
    })),
  });

  if (isError) {
    return (
      <Stack gap="md">
        <BackButton to="/" />
        <ErrorAlert>{t("kp.company_view.error")}</ErrorAlert>
      </Stack>
    );
  }

  if (isPending || bookingQueries.some((query) => query.isPending)) {
    return <PageLoader />;
  }

  const bookedEventIds = new Set(
    events
      .filter((_, index) => activeBooking(bookingQueries[index]?.data))
      .map((event) => event.id),
  );
  const isBooked = (event: KpResponse) => bookedEventIds.has(event.id);

  const currentEvents = events.filter((event) => {
    const status = getEventStatus(event);
    return (
      status === "registration_open" || (status !== "past" && isBooked(event))
    );
  });
  const participatedPastEvents = events.filter(
    (event) => getEventStatus(event) === "past" && isBooked(event),
  );
  const hasBookingError = bookingQueries.some((query) => query.isError);

  return (
    <Stack gap="md">
      <BackButton to="/" />
      <div>
        <Title order={2}>{t("kp.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("kp.history.title")}
        </Text>
      </div>

      {hasBookingError ? <ErrorAlert /> : null}

      {currentEvents.length ? (
        <Stack gap="sm">
          <Text fw={600}>{t("kp.join.current_event")}</Text>
          {currentEvents.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </Stack>
      ) : null}

      {participatedPastEvents.length ? (
        <Stack gap="sm">
          <Text fw={600}>{t("kp.history.title")}</Text>
          {participatedPastEvents.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </Stack>
      ) : currentEvents.length === 0 && !hasBookingError ? (
        <Card withBorder radius="md" p="lg">
          <Text c="dimmed" ta="center">
            {t("kp.history.none")}
          </Text>
        </Card>
      ) : null}
    </Stack>
  );
};
export default KpCompanyEvents;
