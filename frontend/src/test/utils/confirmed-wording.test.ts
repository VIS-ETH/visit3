import { describe, expect, it } from "vitest";
import deCommon from "../../../public/locales/de/common.json";
import deKp from "../../../public/locales/de/kp.json";
import enCommon from "../../../public/locales/en/common.json";
import enKp from "../../../public/locales/en/kp.json";

const confirmedTexts = (locale: typeof enKp, common: typeof enCommon) => [
  locale.kp.booking.status.confirmed.description,
  locale.kp.booking.confirmed_body,
  locale.kp.zone_switch.disabled_confirmed,
  common.error.kp_booking_zone_locked,
];

describe("the confirmed booking wording", () => {
  it.each([
    ["en", enKp, enCommon, "but no longer change the booth zone"],
    ["de", deKp, deCommon, "die Standzone aber nicht mehr ändern"],
  ])("says the same in every %s place", (_, locale, common, zoneSentence) => {
    const texts = confirmedTexts(locale, common);

    expect(new Set(texts).size).toBe(1);
    expect(texts[0]).toContain(zoneSentence);
  });

  it.each([
    ["en", enKp, "You can cancel as long as the booking is not confirmed."],
    [
      "de",
      deKp,
      "Sie können stornieren, solange die Buchung nicht bestätigt ist.",
    ],
  ])(
    "explains in %s until when a booking can be cancelled",
    (_, locale, hint) => {
      expect(locale.kp.booking.cancel_hint).toBe(hint);
    },
  );
});
