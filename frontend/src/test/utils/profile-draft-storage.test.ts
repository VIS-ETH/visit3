import { describe, expect, it } from "vitest";
import { clearAuthState } from "../../api/utils";

describe("company profile drafts", () => {
  it("are forgotten when the session is cleared", () => {
    localStorage.setItem("company-profile-draft:me:company-1", "{}");
    localStorage.setItem("company-profile-draft:staff:company-2", "{}");
    localStorage.setItem("color-scheme", "dark");

    clearAuthState();

    expect(
      localStorage.getItem("company-profile-draft:me:company-1"),
    ).toBeNull();
    expect(
      localStorage.getItem("company-profile-draft:staff:company-2"),
    ).toBeNull();
    expect(localStorage.getItem("color-scheme")).toBe("dark");
  });
});
