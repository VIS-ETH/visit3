import { describe, expect, it } from "vitest";
import { createInstance } from "i18next";
import fs from "node:fs";
import path from "node:path";

const load = (lng: string, ns: string) =>
  JSON.parse(
    fs.readFileSync(
      path.resolve(__dirname, `../../../public/locales/${lng}/${ns}.json`),
      "utf8",
    ),
  );

const make = async (lng: string) => {
  const i18n = createInstance();
  await i18n.init({
    lng,
    ns: ["admin", "account"],
    defaultNS: "admin",
    fallbackNS: ["account"],
    resources: {
      [lng]: { admin: load(lng, "admin"), account: load(lng, "account") },
    },
    interpolation: { escapeValue: false },
  });
  return i18n;
};

describe("company locale strings", () => {
  it("counts a single company in the singular", async () => {
    const i18n = await make("en");
    expect(i18n.t("company_management.total", { count: 1 })).toBe("1 company");
    expect(i18n.t("company_management.total", { count: 2 })).toBe(
      "2 companies",
    );
  });

  it("names a single missing field in the singular", async () => {
    const i18n = await make("en");
    expect(
      i18n.t("company_profile.profile_incomplete_hint", { count: 1 }),
    ).toBe("1 mandatory field is still missing.");
  });

  it("puts the company before the infinitive in German", async () => {
    const i18n = await make("de");
    expect(i18n.t("company_join.joining", { company: "Acme AG" })).toBe(
      "Sie wurden eingeladen, Acme AG beizutreten.",
    );
  });
});
