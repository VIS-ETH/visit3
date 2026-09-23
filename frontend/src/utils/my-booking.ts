import type {
  BookingResponse,
  MyBookingResponse,
} from "../orval/generated/fastAPI.schemas";
import { isActiveBookingStatus } from "./booking-status";

export const isInactiveBooking = (booking: BookingResponse) =>
  !isActiveBookingStatus(booking.status);

export const activeBooking = (booking: MyBookingResponse | null | undefined) =>
  booking && !isInactiveBooking(booking) ? booking : null;

export const canStartNewBooking = (
  booking: MyBookingResponse | null | undefined,
  isRegistrationOpen: boolean,
) => (booking ? booking.can_register : isRegistrationOpen);
