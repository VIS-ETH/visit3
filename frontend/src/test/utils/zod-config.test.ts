import { describe, expect, it } from "vitest";
import { z } from "zod";
import "../../utils/zod-config";

describe("zod configuration", () => {
  it("validates without probing for eval so the CSP stays quiet", () => {
    expect(z.config().jitless).toBe(true);
  });
});
