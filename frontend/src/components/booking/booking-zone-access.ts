import {
  KpBookingStatus,
  type BookingResponse,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";

const toCalendarDate = (date: Date) =>
  `${String(date.getFullYear()).padStart(4, "0")}-${String(
    date.getMonth() + 1,
  ).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

export const isFinalizationDeadlinePassed = (event: KpResponse) =>
  event.finalization_deadline.slice(0, 10) < toCalendarDate(new Date());

export const isBoothZoneLocked = (booking: BookingResponse) =>
  booking.status === KpBookingStatus.CONFIRMED;

export const canSwitchBoothZone = (
  event: KpResponse,
  booking: BookingResponse,
) =>
  booking.status === KpBookingStatus.REGISTERED &&
  !isFinalizationDeadlinePassed(event);
