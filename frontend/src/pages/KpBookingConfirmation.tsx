import {
  Alert,
  Anchor,
  Center,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle, IconCircleCheck } from "@tabler/icons-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import { useGetKpById, useGetMyBooking } from "../orval/generated/kp/kp";
import { KpBookingRecap } from "../components/KpBookingRecap";

const KP_BOOKING_HELP_EMAIL = "info@kontaktparty.ch";

const KpBookingConfirmation = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { id = "", bookingId = "" } = useParams<{
    id: string;
    bookingId: string;
  }>();
  const eventId = id.trim();
  const normalizedBookingId = bookingId.trim();
  const showJustBookedNotice =
    (location.state as { fromBookingProcess?: boolean } | null)
      ?.fromBookingProcess === true;

  const {
    data: event,
    isLoading: isLoadingEvent,
    isError: isEventError,
  } = useGetKpById(eventId, {
    query: { enabled: Boolean(eventId) },
  });

  const {
    data: booking,
    isLoading: isLoadingBooking,
    isFetching: isFetchingBooking,
    isError: isBookingError,
  } = useGetMyBooking(eventId, {
    query: { enabled: Boolean(eventId) },
  });

  useEffect(() => {
    if (!eventId || !normalizedBookingId) {
      navigate("/kp", { replace: true });
      return;
    }
    if (isLoadingEvent || isLoadingBooking || isFetchingBooking) return;
    if (
      isEventError ||
      isBookingError ||
      !event ||
      !booking ||
      booking.id !== normalizedBookingId
    ) {
      navigate(`/kp/${eventId}/booking`, { replace: true });
    }
  }, [
    eventId,
    normalizedBookingId,
    isLoadingEvent,
    isLoadingBooking,
    isFetchingBooking,
    isEventError,
    isBookingError,
    event,
    booking,
    navigate,
  ]);

  const showBookingLoader =
    isLoadingEvent || isLoadingBooking || isFetchingBooking;

  if (showBookingLoader) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }

  if (
    !eventId ||
    !normalizedBookingId ||
    isEventError ||
    isBookingError ||
    !event ||
    !booking ||
    booking.id !== normalizedBookingId
  ) {
    return (
      <Stack gap="md">
        <BackButton to={eventId ? `/kp/${eventId}/booking` : "/kp"} />
        <Alert
          radius="md"
          icon={<IconAlertCircle />}
          color="red"
          title={t("server.error")}
        >
          {t("kp.booking.error")}
        </Alert>
      </Stack>
    );
  }

  const supportSubject = `[${event.name}] - Booking #${booking.booking_number ?? "-"}`;

  return (
    <Stack gap="md">
      <BackButton to={`/kp/${eventId}`} />
      <div>
        <Title order={2}>
          {t("kp.booking.summary_title")} (
          {booking.booking_number != null ? `#${booking.booking_number}` : "-"})
        </Title>
        <Text c="dimmed" size="sm" mt={4}>
          {event.name}
        </Text>
      </div>

      {showJustBookedNotice ? (
        <Alert
          variant="light"
          color="green"
          radius="md"
          icon={<IconCircleCheck size={22} stroke={1.5} />}
          title={t("kp.booking.confirmation_just_booked_headline")}
        >
          <Text size="sm" mt={4}>
            {t("kp.booking.confirmation_just_booked_body", {
              eventName: event.name,
            })}
          </Text>
        </Alert>
      ) : null}

      <KpBookingRecap booking={booking} />

      <Text size="sm" c="dimmed">
        {t("kp.booking.confirmation_help_footer_prompt")}{" "}
        <Anchor
          href={`mailto:${KP_BOOKING_HELP_EMAIL}?subject=${encodeURIComponent(supportSubject)}`}
          size="sm"
          fw={500}
        >
          {t("kp.booking.confirmation_help_contact_us")}
        </Anchor>
      </Text>
    </Stack>
  );
};
export default KpBookingConfirmation;
