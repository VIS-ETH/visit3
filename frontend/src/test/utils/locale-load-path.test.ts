import { describe, expect, it } from "vitest";
import { LOCALE_LOAD_PATH } from "../../utils/locale-load-path";

describe("the locale load path", () => {
  it("asks for the locale files of this build", () => {
    const [path, version] = LOCALE_LOAD_PATH.split("?v=");

    expect(path).toBe("/locales/{{lng}}/{{ns}}.json");
    expect(version).toMatch(/^[a-z0-9]+$/);
  });
});
