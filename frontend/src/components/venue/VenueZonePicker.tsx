import { useCallback } from "react";
import type { BoothZoneWithAvailabilityResponse } from "../../orval/generated/fastAPI.schemas";
import { useGetEventVenue } from "../../orval/generated/kp/kp";
import VenueMapViewer from "./VenueMapViewer";

interface VenueZonePickerProps {
  eventId: string;
  selectedZone: BoothZoneWithAvailabilityResponse | null;
  onSelectZone: (zone: BoothZoneWithAvailabilityResponse) => void;
}

const VenueZonePicker = ({
  eventId,
  selectedZone,
  onSelectZone,
}: VenueZonePickerProps) => {
  const { data: venue } = useGetEventVenue(eventId);

  const handleSelectZone = useCallback(
    (zoneId: string) => {
      const zone = venue?.zones.find((candidate) => candidate.id === zoneId);
      if (zone) onSelectZone(zone);
    },
    [venue, onSelectZone],
  );

  return (
    <VenueMapViewer
      eventId={eventId}
      onSelectZone={handleSelectZone}
      selectedZoneId={selectedZone?.id ?? null}
    />
  );
};

export default VenueZonePicker;
