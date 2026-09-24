import { KpBookingStatus } from "../orval/generated/fastAPI.schemas";

export const BOOKING_STATUS_ORDER: readonly KpBookingStatus[] = [
  KpBookingStatus.REGISTERED,
  KpBookingStatus.CONFIRMED,
  KpBookingStatus.CANCELLED,
  KpBookingStatus.REJECTED,
];

const ACTIVE_BOOKING_STATUSES: readonly KpBookingStatus[] = [
  KpBookingStatus.REGISTERED,
  KpBookingStatus.CONFIRMED,
];

export const canAcceptBooking = (status: KpBookingStatus) =>
  status === KpBookingStatus.REGISTERED;

export const canUndoAcceptBooking = (status: KpBookingStatus) =>
  status === KpBookingStatus.CONFIRMED;

export const canRejectBooking = (status: KpBookingStatus) =>
  status === KpBookingStatus.REGISTERED;

export const deleteRequiresForce = (status: KpBookingStatus) =>
  status === KpBookingStatus.CONFIRMED;

export const isActiveBookingStatus = (status: KpBookingStatus) =>
  ACTIVE_BOOKING_STATUSES.includes(status);

export const bookingStatusRank = (status: KpBookingStatus) =>
  BOOKING_STATUS_ORDER.indexOf(status);
