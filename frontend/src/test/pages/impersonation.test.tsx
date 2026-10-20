import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import UserManagement from "../../pages/UserManagement";
import RootLayout from "../../pages/root";
import { UserProvider } from "../../context/UserContext";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { getImpersonatingUserId, setImpersonation } from "../../api/utils";
import { reloadAt } from "../../utils/navigation";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";

vi.mock("../../utils/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../utils/navigation")>()),
  reloadAt: vi.fn(),
}));

const adminUser: UserResponse = {
  id: "admin-1",
  email: "admin@example.com",
  is_staff: true,
  is_admin: true,
  is_company: false,
  is_kp_president: true,
  email_confirmed: true,
};

const companyUser = {
  id: "user-9",
  email: "member@example.com",
  first_name: "Mem",
  last_name: "Ber",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  email_confirmed: true,
};

beforeEach(() => {
  vi.mocked(reloadAt).mockClear();
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/users`, () =>
      HttpResponse.json({
        items: [companyUser],
        total: 1,
        page: 1,
        page_size: 25,
      }),
    ),
  );
});

describe("starting an impersonation", () => {
  it("reloads as the user and remembers the user management search", async () => {
    const { user } = renderWithProviders(
      <UserProvider user={adminUser} isLoading={false}>
        <UserManagement />
      </UserProvider>,
      { route: "/user-management?query=mem" },
    );

    await user.click(
      await screen.findByRole("button", {
        name: "user_management.impersonate",
      }),
    );

    expect(getImpersonatingUserId()).toBe(companyUser.id);
    expect(sessionStorage.getItem("impersonation_origin")).toBe(
      "/user-management?query=mem",
    );
    expect(reloadAt).toHaveBeenCalledWith("/");
  });
});

describe("stopping an impersonation", () => {
  it.each([
    ["/company-management?page=2", "/company-management?page=2"],
    ["//evil.example/phish", "/"],
    ["https://evil.example/phish", "/"],
    [undefined, "/"],
  ])("returns from %s to %s", async (origin, expected) => {
    setImpersonation(companyUser.id, "Mem Ber", origin);
    const { user } = renderWithProviders(
      <UserProvider user={adminUser} isLoading={false}>
        <RootLayout navbarHidden={false} />
      </UserProvider>,
      { route: "/company" },
    );

    await user.click(
      await screen.findByRole("button", { name: "impersonation.stop" }),
    );

    await waitFor(() => {
      expect(reloadAt).toHaveBeenCalledWith(expected);
    });
    expect(getImpersonatingUserId()).toBeNull();
    expect(sessionStorage.getItem("impersonation_origin")).toBeNull();
  });
});
