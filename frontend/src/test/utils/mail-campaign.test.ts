import { describe, expect, it } from "vitest";
import {
  conditionalParagraph,
  isFutureZurichInput,
  nextFullHourInput,
  serviceCondition,
  toMailCampaignRequest,
  zurichDateTimeInput,
} from "../../utils/mail-campaign";

describe("the Zurich schedule input", () => {
  it.each([
    ["2030-07-01T07:00:00Z", "2030-07-01T09:00"],
    ["2030-12-01T08:00:00Z", "2030-12-01T09:00"],
    ["2030-10-27T00:30:00Z", "2030-10-27T02:30"],
    ["2030-12-31T23:15:00Z", "2031-01-01T00:15"],
  ])("shows %s as %s", (instant, expected) => {
    expect(zurichDateTimeInput(new Date(instant))).toBe(expected);
  });

  it("suggests the next full hour", () => {
    expect(nextFullHourInput(new Date("2030-07-01T07:20:00Z"))).toBe(
      "2030-07-01T10:00",
    );
  });

  it("only accepts times after now", () => {
    const now = new Date("2030-07-01T07:00:00Z");

    expect(isFutureZurichInput("2030-07-01T09:01", now)).toBe(true);
    expect(isFutureZurichInput("2030-07-01T09:00", now)).toBe(false);
    expect(isFutureZurichInput("2030-07-01T08:30", now)).toBe(false);
  });
});

describe("the campaign request", () => {
  it("trims the subjects and keeps the audience", () => {
    expect(
      toMailCampaignRequest({
        name: " Reminder ",
        eventId: "event-1",
        subjectDe: " Erinnerung ",
        bodyDe: "<p>Hallo</p>",
        subjectEn: "  ",
        bodyEn: "",
        segments: ["NOT_REGISTERED", "OFFERED"],
        boothZoneIds: ["zone-1"],
        includeCompanyIds: ["company-1"],
        excludeCompanyIds: ["company-2"],
        bookedServices: ["BOOTH_ELEMENT", "service-1"],
        allAccounts: true,
      }),
    ).toEqual({
      name: "Reminder",
      event_id: "event-1",
      subject_de: "Erinnerung",
      body_de: "<p>Hallo</p>",
      subject_en: "",
      body_en: "",
      audience: {
        segments: ["NOT_REGISTERED", "OFFERED"],
        booth_zone_ids: ["zone-1"],
        include_company_ids: ["company-1"],
        exclude_company_ids: ["company-2"],
        service_ids: ["service-1"],
        service_categories: ["BOOTH_ELEMENT"],
        all_accounts: true,
      },
    });
  });
});

describe("the service paragraphs", () => {
  it("quotes service names for the condition", () => {
    expect(
      serviceCondition({
        id: "service-1",
        name: 'Tisch "XL"',
        category: "BOOTH_ELEMENT",
        order: 1,
      }),
    ).toBe('"Tisch \\"XL\\"" in booth_elements');
    expect(serviceCondition("SERVICE")).toBe("services");
  });

  it("puts the caret into an empty paragraph", () => {
    const { snippet, caret } = conditionalParagraph("services", "");

    expect(snippet).toBe("{% if services %}<p></p>{% endif %}");
    expect(snippet.slice(0, caret)).toBe("{% if services %}<p>");
  });
});
