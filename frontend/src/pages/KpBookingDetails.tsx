import {
  Alert,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useContext, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import BackButton from "../components/BackButton";
import ErrorAlert from "../components/ErrorAlert";
import { KpBookingStatusBadge } from "../components/KpBookingStatusBadge";
import PageLoader from "../components/PageLoader";
import BookingActionBar from "../components/staff-bookings/BookingActionBar";
import BookingCompletenessCard from "../components/staff-bookings/BookingCompletenessCard";
import BookingEditPanel from "../components/staff-bookings/BookingEditPanel";
import BookingNametagsCard from "../components/staff-bookings/BookingNametagsCard";
import BookingOfferCard from "../components/staff-bookings/BookingOfferCard";
import BookingServicesCard from "../components/staff-bookings/BookingServicesCard";
import BookingStatusTimeline from "../components/staff-bookings/BookingStatusTimeline";
import BookingWaitlistCard from "../components/staff-bookings/BookingWaitlistCard";
import VenueMapViewer from "../components/venue/VenueMapViewer";
import { UserContext } from "../context/useCurrentUser";
import { KpBookingStatus } from "../orval/generated/fastAPI.schemas";
import { useGetEventBooking } from "../orval/generated/kp/kp";
import { getApiErrorCode, getApiErrorStatus } from "../api/errors";
import { formatMoney } from "../utils/money";

const NOT_ALLOWED_CODE = "error.not_allowed";
const INLINE_ERROR_STATUSES = [403, 404];

const DetailField = ({ label, value }: { label: string; value: ReactNode }) => (
  <Stack gap={2}>
    <Text c="dimmed" size="sm">
      {label}
    </Text>
    {typeof value === "string" || typeof value === "number" ? (
      <Text fw={500}>{value}</Text>
    ) : (
      value
    )}
  </Stack>
);

const KpBookingDetails = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id, bookingId } = useParams<{ id: string; bookingId: string }>();
  const backToBookings = id ? `/kp/${id}?tab=bookings` : "/kp";
  const {
    data: booking,
    error,
    isError,
    isLoading,
  } = useGetEventBooking(id ?? "", bookingId ?? "", {
    query: { enabled: Boolean(id && bookingId), retry: false },
    request: { quietStatuses: INLINE_ERROR_STATUSES },
  });
  const isForbidden = getApiErrorCode(error) === NOT_ALLOWED_CODE;
  const isMissing = !isError || getApiErrorStatus(error) === 404;
  const isPresident = useContext(UserContext)?.user?.is_kp_president ?? false;

  if (!id || !bookingId) {
    return (
      <Stack gap="md">
        <BackButton to="/kp" />
        <ErrorAlert>{t("kp.manage.booking_detail_not_found")}</ErrorAlert>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack gap="md">
        <BackButton to={backToBookings} />
        <PageLoader />
      </Stack>
    );
  }

  if (isError || !booking) {
    return (
      <Stack gap="md">
        <BackButton to={backToBookings} />
        {isForbidden ? (
          <Alert
            icon={<IconAlertCircle />}
            color="yellow"
            title={t("not_allowed.title")}
          >
            {t("kp.manage.booking_detail_forbidden")}
          </Alert>
        ) : (
          <ErrorAlert>
            {isMissing ? t("kp.manage.booking_detail_not_found") : undefined}
          </ErrorAlert>
        )}
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <BackButton to={backToBookings} />

      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>
            {t("kp.manage.booking_detail_title", {
              bookingNumber: booking.booking_number,
            })}
          </Title>
          <Text c="dimmed" size="sm">
            {booking.company.name}
          </Text>
        </div>
        <KpBookingStatusBadge size="lg" status={booking.status} />
      </Group>

      <Paper withBorder p="lg" radius="md">
        <Stack gap="lg">
          <Title order={4}>{t("kp.manage.booking_timeline_title")}</Title>
          <BookingStatusTimeline booking={booking} />
        </Stack>
      </Paper>

      <BookingActionBar
        booking={booking}
        eventId={id}
        onDeleted={() => {
          void navigate(backToBookings);
        }}
      />

      <BookingCompletenessCard booking={booking} />

      {booking.status === KpBookingStatus.OFFERED ? (
        <BookingOfferCard
          booking={booking}
          eventId={id}
          canEdit={isPresident}
        />
      ) : null}

      <BookingEditPanel key={booking.id} booking={booking} eventId={id} />

      <BookingWaitlistCard booking={booking} />

      <Paper withBorder p="lg" radius="md">
        <Stack gap="lg">
          <Title order={4}>{t("kp.manage.booking_detail_overview")}</Title>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
            <DetailField
              label={t("kp.manage.booking_company")}
              value={booking.company.name}
            />
            <DetailField
              label={t("kp.manage.booking_booth_zone")}
              value={booking.booth_zone.name}
            />
            <DetailField
              label={t("kp.manage.booking_booth_nr")}
              value={booking.booth_nr ?? "-"}
            />
            <DetailField
              label={t("kp.manage.booking_total")}
              value={formatMoney(booking.net_total)}
            />
            <DetailField
              label={t("kp.manage.booking_gross_total")}
              value={formatMoney(booking.price.gross)}
            />
            <DetailField
              label={t("kp.manage.booking_nametags")}
              value={booking.nametag_count}
            />
            <DetailField
              label={t("kp.manage.booking_waitlist")}
              value={booking.waitlist_count}
            />
          </SimpleGrid>
        </Stack>
      </Paper>

      <BookingNametagsCard bookingId={booking.id} />

      <Paper withBorder p="lg" radius="md">
        <Stack gap="md">
          <Title order={4}>{t("kp.venue.booking_map_title")}</Title>
          <VenueMapViewer
            eventId={id}
            highlightBooth={{
              zoneId: booking.booth_zone_id,
              boothNr: booking.booth_nr,
            }}
            selectedZoneId={booking.booth_zone_id}
          />
        </Stack>
      </Paper>

      <BookingServicesCard booking={booking} eventId={id} />
    </Stack>
  );
};

export default KpBookingDetails;
