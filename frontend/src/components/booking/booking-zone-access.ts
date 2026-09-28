import {
  KpBookingStatus,
  type BookingResponse,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import { isDeadlinePassed } from "../../utils/kp-utils";

export const isFinalizationDeadlinePassed = (event: KpResponse) =>
  isDeadlinePassed(event.finalization_deadline);

export const isBoothZoneLocked = (booking: BookingResponse) =>
  booking.status === KpBookingStatus.CONFIRMED;

export const canSwitchBoothZone = (
  event: KpResponse,
  booking: BookingResponse,
) =>
  booking.status === KpBookingStatus.REGISTERED &&
  !isFinalizationDeadlinePassed(event);
