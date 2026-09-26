import { describe, expect, it } from "vitest";
import deCommon from "../../../public/locales/de/common.json";
import enCommon from "../../../public/locales/en/common.json";

const ERROR_KEYS = [
  "mail_unavailable",
  "company_name_taken",
  "conflict",
  "internal",
  "network",
  "reference",
] as const;

describe("the error messages for user-important failures", () => {
  it.each([
    ["en", enCommon],
    ["de", deCommon],
  ])("exist in %s", (_, locale) => {
    const errors = locale.error as Record<string, string>;

    for (const key of ERROR_KEYS) {
      expect(errors[key], key).toBeTruthy();
    }
    expect(locale.server.error).not.toBe("Server error");
  });
});
