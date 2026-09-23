import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";
import {
  MANDATORY_PROFILE_FIELDS,
  mandatoryFieldLabelKey,
} from "../../components/company/company-profile-fields";
import { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import {
  BOOKING_STATUS_DESCRIPTION_KEYS,
  BOOKING_STATUS_LABEL_KEYS,
  EVENT_STATUS_COLORS,
  type EventStatus,
} from "../../utils/kp-utils";

const frontendRoot = process.cwd();
const localeRootDir = path.join(frontendRoot, "public", "locales");
const companyModelFile = path.join(
  frontendRoot,
  "..",
  "backend",
  "app",
  "models",
  "company.py",
);

const LOCALES = ["en", "de"] as const;

const flattenKeys = (value: unknown, prefix = ""): string[] => {
  if (typeof value !== "object" || value === null)
    return prefix ? [prefix] : [];
  return Object.entries(value).flatMap(([key, nested]) =>
    flattenKeys(nested, prefix ? `${prefix}.${key}` : key),
  );
};

const localeKeys = (locale: string) => {
  const localeDir = path.join(localeRootDir, locale);
  return new Set(
    fs
      .readdirSync(localeDir)
      .filter((file) => file.endsWith(".json"))
      .flatMap((file) =>
        flattenKeys(
          JSON.parse(fs.readFileSync(path.join(localeDir, file), "utf8")),
        ),
      ),
  );
};

const keysByLocale = new Map(
  LOCALES.map((locale) => [locale, localeKeys(locale)] as const),
);

const missingLocales = (key: string) =>
  LOCALES.filter((locale) => !keysByLocale.get(locale)?.has(key));

const expectKeysInBothLocales = (keys: string[]) => {
  const missing = keys.flatMap((key) =>
    missingLocales(key).map((locale) => `${locale}: ${key}`),
  );
  expect(missing).toEqual([]);
};

const backendMandatoryProfileFields = () => {
  const source = fs.readFileSync(companyModelFile, "utf8");
  const start = source.indexOf("MANDATORY_PROFILE_FIELDS = (");
  const end = source.indexOf(")", start);
  return [...source.slice(start, end).matchAll(/"(\w+)"/g)].map(
    (match) => match[1],
  );
};

const eventStatuses = Object.keys(EVENT_STATUS_COLORS) as EventStatus[];
const bookingStatuses = Object.values(KpBookingStatus);

describe("the mandatory profile fields", () => {
  it("match the backend definition", () => {
    expect([...MANDATORY_PROFILE_FIELDS]).toEqual(
      backendMandatoryProfileFields(),
    );
  });

  it("have a booking wizard label in both locales", () => {
    expectKeysInBothLocales(
      MANDATORY_PROFILE_FIELDS.map(
        (field) => `kp.booking.profile_field.${field}`,
      ),
    );
  });

  it("have a profile form label in both locales", () => {
    expectKeysInBothLocales(
      MANDATORY_PROFILE_FIELDS.map((field) => mandatoryFieldLabelKey(field)),
    );
  });
});

describe("the event statuses", () => {
  it("have a company view label in both locales", () => {
    expect(eventStatuses.length).toBeGreaterThan(0);
    expectKeysInBothLocales(
      eventStatuses.map((status) => `kp.company_view.status_${status}`),
    );
  });
});

describe("the booking statuses", () => {
  it("have a label and a description in both locales", () => {
    expect(bookingStatuses.length).toBeGreaterThan(0);
    expectKeysInBothLocales(
      bookingStatuses.flatMap((status) => [
        BOOKING_STATUS_LABEL_KEYS[status],
        BOOKING_STATUS_DESCRIPTION_KEYS[status],
      ]),
    );
  });
});
