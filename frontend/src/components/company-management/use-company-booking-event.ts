import { useState } from "react";
import type { StaffBookingResponse } from "../../orval/generated/fastAPI.schemas";
import { useListEventBookings, useListKps } from "../../orval/generated/kp/kp";
import { isActiveBookingStatus } from "../../utils/booking-status";
import { getEventStatus } from "../../utils/kp-utils";

export const useCompanyBookingEvent = () => {
  const { data: events, isLoading: isLoadingEvents } = useListKps();
  const [pickedEventId, setPickedEventId] = useState<string | null>(null);
  const latestEvent = events?.at(0);
  const upcomingEvent =
    latestEvent && getEventStatus(latestEvent) !== "past" ? latestEvent : null;
  const bookingEvent =
    events?.find((event) => event.id === pickedEventId) ??
    upcomingEvent ??
    null;
  const { data: eventBookings } = useListEventBookings(bookingEvent?.id ?? "", {
    query: { enabled: bookingEvent !== null },
  });
  const activeBookingByCompanyId = new Map<string, StaffBookingResponse>(
    (eventBookings ?? [])
      .filter((booking) => isActiveBookingStatus(booking.status))
      .map((booking) => [booking.company_id, booking]),
  );

  return {
    events: events ?? [],
    isLoadingEvents,
    bookingEvent,
    pickEvent: setPickedEventId,
    activeBookingByCompanyId,
  };
};
