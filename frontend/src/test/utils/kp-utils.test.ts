import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { formatKpIsoDateInput, getEventStatus } from "../../utils/kp-utils";
import type { KpResponse } from "../../orval/generated/fastAPI.schemas";

const timeZones = ["Europe/Zurich", "America/New_York", "UTC"];
const wallClocks = ["00:30", "23:30"];

const event: KpResponse = {
  id: "event-1",
  name: "KP 2026",
  registration_open: "2026-03-01",
  registration_end: "2026-03-31",
  finalization_deadline: "2026-04-10",
  nametags_deadline: "2026-04-15",
  event_date: "2026-04-20",
  vat_rate_percent: 8.1,
  terms_url: null,
  finalization_reminder_days: 3,
  max_nametags_per_booking: 5,
};

const zonedParts = (instant: Date, timeZone: string) => {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(instant);

  return Object.fromEntries(parts.map((part) => [part.type, part.value]));
};

const instantAtWallClock = (
  calendarDate: string,
  wallClock: string,
  timeZone: string,
) => {
  const target = Date.parse(`${calendarDate}T${wallClock}:00Z`);
  let instant = new Date(target);

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const parts = zonedParts(instant, timeZone);
    const seen = Date.parse(
      `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}Z`,
    );
    instant = new Date(instant.getTime() + (target - seen));
  }

  return instant;
};

const freezeLocalTime = (
  calendarDate: string,
  wallClock: string,
  timeZone: string,
) => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(instantAtWallClock(calendarDate, wallClock, timeZone));
};

describe.each(timeZones)("getEventStatus under TZ=%s", (timeZone) => {
  beforeEach(() => {
    vi.stubEnv("TZ", timeZone);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
  });

  it.each(wallClocks)(
    "is registration_open on the first day of the window at %s local time",
    (wallClock) => {
      freezeLocalTime("2026-03-01", wallClock, timeZone);

      expect(getEventStatus(event)).toBe("registration_open");
    },
  );

  it.each(wallClocks)(
    "is registration_open on the last day of the window at %s local time",
    (wallClock) => {
      freezeLocalTime("2026-03-31", wallClock, timeZone);

      expect(getEventStatus(event)).toBe("registration_open");
    },
  );

  it.each(wallClocks)(
    "is upcoming on the day before the window opens at %s local time",
    (wallClock) => {
      freezeLocalTime("2026-02-28", wallClock, timeZone);

      expect(getEventStatus(event)).toBe("upcoming");
    },
  );

  it.each(wallClocks)(
    "is not past on the event day at %s local time",
    (wallClock) => {
      freezeLocalTime("2026-04-20", wallClock, timeZone);

      expect(getEventStatus(event)).toBe("upcoming");
    },
  );

  it.each(wallClocks)(
    "is past on the day after the event at %s local time",
    (wallClock) => {
      freezeLocalTime("2026-04-21", wallClock, timeZone);

      expect(getEventStatus(event)).toBe("past");
    },
  );

  it("pads single digit months and days before comparing today with the window", () => {
    freezeLocalTime("2026-01-05", "12:00", timeZone);

    expect(
      getEventStatus({
        ...event,
        registration_open: "2026-01-05",
        registration_end: "2026-01-15",
        event_date: "2026-01-20",
      }),
    ).toBe("registration_open");
  });
});

describe("formatKpIsoDateInput", () => {
  it("renders an iso calendar date as a swiss date", () => {
    expect(formatKpIsoDateInput("2026-01-01")).toBe("01.01.2026");
  });

  it("ignores the time part of an iso timestamp", () => {
    expect(formatKpIsoDateInput("2026-01-01T23:45:00Z")).toBe("01.01.2026");
  });

  it("renders an empty string for a missing or unparsable value", () => {
    expect(formatKpIsoDateInput(null)).toBe("");
    expect(formatKpIsoDateInput(undefined)).toBe("");
    expect(formatKpIsoDateInput("01.01.2026")).toBe("");
  });
});
