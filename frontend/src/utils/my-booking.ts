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

export const isPendingOffer = (booking: BookingResponse) =>
  booking.status === KpBookingStatus.OFFERED;

export const isOfferOpen = (booking: BookingResponse) =>
  isPendingOffer(booking) && !isDeadlinePassed(booking.offer_deadline ?? "");

export const isManageableBooking = (booking: BookingResponse) =>
  !isInactiveBooking(booking) && !isPendingOffer(booking);
