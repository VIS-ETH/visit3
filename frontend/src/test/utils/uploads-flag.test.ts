import { describe, expect, it } from "vitest";
import { uploadsAvailable } from "../../utils/uploads";

describe("the uploads flag", () => {
  it("turns uploads off only for an explicit true", () => {
    expect(uploadsAvailable("true")).toBe(false);
  });

  it.each([
    undefined,
    "",
    "false",
    "TRUE",
    "1",
    "yes",
    " true",
    "${VISIT_UPLOADS_UNAVAILABLE}",
    "%VITE_VISIT_UPLOADS_UNAVAILABLE%",
  ])("keeps uploads on for %j", (value) => {
    expect(uploadsAvailable(value)).toBe(true);
  });
});
