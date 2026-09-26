import { describe, expect, it } from "vitest";
import { getSafeNextPath } from "../../utils/navigation";

const resolvesOffsite = (path: string) =>
  new URL(path, "https://visit.vis.ethz.ch").origin !==
  "https://visit.vis.ethz.ch";

describe("getSafeNextPath", () => {
  it.each([
    "?next=%2F%5Cevil.example%2Fphish",
    "?next=%2F%5C%5Cevil.example%2Fphish",
    "?next=%2F%09%2Fevil.example%2Fphish",
    "?next=%2F%0A%2Fevil.example%2Fphish",
  ])("never returns a path that leaves the portal for %s", (search) => {
    const next = getSafeNextPath(search);

    expect(next === null || !resolvesOffsite(next)).toBe(true);
  });

  it("keeps an in-app path", () => {
    expect(getSafeNextPath("?next=%2Fkp%2Fevent-1%2Fbooking")).toBe(
      "/kp/event-1/booking",
    );
  });
});
