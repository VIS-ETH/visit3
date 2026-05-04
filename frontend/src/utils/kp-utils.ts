import type {
  KpBookingStatus,
  KpResponse,
} from "../orval/generated/fastAPI.schemas";

export type EventStatus = "upcoming" | "registration_open" | "past";
const DATE_INPUT_PATTERN = /^(\d{2})\.(\d{2})\.(\d{4})$/;

function buildUtcDate(day: number, month: number, year: number) {
  return new Date(Date.UTC(year, month - 1, day));
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

export function toKpIsoDate(value: string) {
  const parsed = parseKpDateInput(value);
  if (!parsed) {
    throw new Error(`Invalid KP date input: ${value}`);
  }

  return parsed.toISOString().slice(0, 10);
}

export function getEventStatus(event: KpResponse): EventStatus {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const regOpen = event.registration_open
    ? new Date(event.registration_open)
    : null;
  const regEnd = event.registration_end
    ? new Date(event.registration_end)
    : null;
  const eventDate = event.event_date ? new Date(event.event_date) : null;

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
  DRAFT: "gray",
  REGISTERED: "blue",
  FINALIZED: "yellow",
  CONFIRMED: "green",
  CANCELLED: "red",
};
