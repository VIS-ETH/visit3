import { Alert, Grid, Text } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  KpResponse,
} from "../../../orval/generated/fastAPI.schemas";
import ErrorAlert from "../../ErrorAlert";
import PageLoader from "../../PageLoader";
import FloorPlanImages from "../../venue/FloorPlanImages";
import KpBookingZoneSelector from "../KpBookingZoneSelector";

interface KpBookingZoneStepProps {
  event: KpResponse;
  selectedZone: BoothZoneWithAvailabilityResponse | null;
  onSelectZone: (zone: BoothZoneWithAvailabilityResponse | null) => void;
  myBooking: BookingResponse | null | undefined;
  isLoadingBooking: boolean;
  isBookingError: boolean;
  isRegistrationOpen: boolean;
}

const KpBookingZoneStep = ({
  event,
  selectedZone,
  onSelectZone,
  myBooking,
  isLoadingBooking,
  isBookingError,
  isRegistrationOpen,
}: KpBookingZoneStepProps) => {
  const { t } = useTranslation();

  if (isLoadingBooking) return <PageLoader />;

  if (isBookingError) return <ErrorAlert />;

  if (!isRegistrationOpen && !myBooking) {
    return (
      <Alert icon={<IconAlertCircle />} color="yellow" mt="xs">
        {t("kp.booking.registration_closed")}
      </Alert>
    );
  }

  return (
    <Grid mt="xs" gap="lg">
      <Grid.Col span={{ base: 12, md: 7 }}>
        <Text fw={600} mb="sm">
          {t("kp.booking.venue_map_title")}
        </Text>
        <FloorPlanImages />
      </Grid.Col>

      <Grid.Col span={{ base: 12, md: 5 }}>
        <Text fw={600} mb="sm">
          {t("kp.booking.select_zone")}
        </Text>
        <KpBookingZoneSelector
          eventId={event.id}
          currentBooking={myBooking}
          selectedZone={selectedZone}
          onSelectZone={onSelectZone}
        />
      </Grid.Col>
    </Grid>
  );
};

export default KpBookingZoneStep;
