import type {
  KpBookingStatus,
  KpResponse,
} from "../orval/generated/fastAPI.schemas";

export type EventStatus = "upcoming" | "registration_open" | "past";
const DATE_INPUT_PATTERN = /^(\d{2})\.(\d{2})\.(\d{4})$/;
const ISO_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})/;

function buildUtcDate(day: number, month: number, year: number) {
  return new Date(Date.UTC(year, month - 1, day));
}

function toCalendarDate(year: number, month: number, day: number) {
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function todayCalendarDate() {
  const now = new Date();
  return toCalendarDate(now.getFullYear(), now.getMonth() + 1, now.getDate());
}

function toCalendarDateOrNull(value?: string | null) {
  const match = value ? ISO_DATE_PATTERN.exec(value) : null;
  return match ? match[0] : null;
}

export function parseKpDateInput(value: string): Date | null {
  const match = DATE_INPUT_PATTERN.exec(value.trim());
  if (!match) {
    return null;
  }

  const [, dayString, monthString, yearString] = match;
  const day = Number(dayString);
  const month = Number(monthString);
  const year = Number(yearString);
  const date = buildUtcDate(day, month, year);

  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }

  return date;
}

export function formatKpDateInput(date: Date) {
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}.${month}.${year}`;
}

export function formatKpIsoDateInput(value?: string | null) {
  const calendarDate = toCalendarDateOrNull(value);
  if (!calendarDate) return "";

  const [year, month, day] = calendarDate.split("-");
  return `${day}.${month}.${year}`;
}

export function formatKpDisplayDate(dateString?: string) {
  if (!dateString) return "-";

  const [yearString, monthString, dayString] = dateString.split("-");
  const year = Number(yearString);
  const month = Number(monthString);
  const day = Number(dayString);

  if (!year || !month || !day) return "-";

  const date = new Date(Date.UTC(year, month - 1, day));
  return new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function isDeadlinePassed(deadline: string) {
  const calendarDate = toCalendarDateOrNull(deadline);
  return calendarDate !== null && calendarDate < todayCalendarDate();
}

export function toKpIsoDate(value: string) {
  const parsed = parseKpDateInput(value);
  if (!parsed) {
    throw new Error(`Invalid KP date input: ${value}`);
  }

  return parsed.toISOString().slice(0, 10);
}

export function getEventStatus(event: KpResponse): EventStatus {
  const today = todayCalendarDate();

  const regOpen = toCalendarDateOrNull(event.registration_open);
  const regEnd = toCalendarDateOrNull(event.registration_end);
  const eventDate = toCalendarDateOrNull(event.event_date);

  if (eventDate && today > eventDate) return "past";

  if (regOpen && regEnd && today >= regOpen && today <= regEnd) {
    return "registration_open";
  }
  return "upcoming";
}

export const EVENT_STATUS_COLORS: Record<EventStatus, string> = {
  upcoming: "blue",
  registration_open: "green",
  past: "gray",
};

export const BOOKING_STATUS_COLORS: Record<KpBookingStatus, string> = {
  REGISTERED: "blue",
  FINALIZED: "yellow",
  CONFIRMED: "green",
  CANCELLED: "red",
  REJECTED: "red",
};

export const BOOKING_STATUS_LABEL_KEYS: Record<KpBookingStatus, string> = {
  REGISTERED: "kp.booking.status.registered.label",
  FINALIZED: "kp.booking.status.finalized.label",
  CONFIRMED: "kp.booking.status.confirmed.label",
  CANCELLED: "kp.booking.status.cancelled.label",
  REJECTED: "kp.booking.status.rejected.label",
};

export const BOOKING_STATUS_DESCRIPTION_KEYS: Record<KpBookingStatus, string> =
  {
    REGISTERED: "kp.booking.status.registered.description",
    FINALIZED: "kp.booking.status.finalized.description",
    CONFIRMED: "kp.booking.status.confirmed.description",
    CANCELLED: "kp.booking.status.cancelled.description",
    REJECTED: "kp.booking.status.rejected.description",
  };
