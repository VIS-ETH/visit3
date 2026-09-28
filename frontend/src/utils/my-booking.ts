import {
  KpBookingStatus,
  type BookingResponse,
  type MyBookingResponse,
} from "../orval/generated/fastAPI.schemas";
import { isDeadlinePassed } from "./kp-utils";
import { isActiveBookingStatus } from "./booking-status";

export const isInactiveBooking = (booking: BookingResponse) =>
  !isActiveBookingStatus(booking.status);

export const activeBooking = (booking: MyBookingResponse | null | undefined) =>
  booking && !isInactiveBooking(booking) ? booking : null;

export const canStartNewBooking = (
  booking: MyBookingResponse | null | undefined,
  isRegistrationOpen: boolean,
) => (booking ? booking.can_register : isRegistrationOpen);

export const isOfferCancellable = (booking: BookingResponse) =>
  Boolean(booking.offer_cancel_until) &&
  !isDeadlinePassed(booking.offer_cancel_until ?? "");

export const canCompanyCancel = (booking: BookingResponse) =>
  booking.offer_cancel_until
    ? isOfferCancellable(booking) && !isInactiveBooking(booking)
    : booking.status === KpBookingStatus.REGISTERED;
