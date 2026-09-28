import { beforeEach, describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../../App";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { adminUser, staffUser } from "../fixtures/admin";
import { testOpenEvent } from "../fixtures/kp-booking";

const companyUser: UserResponse = {
  ...staffUser,
  id: "company-1",
  email: "company@example.test",
  is_staff: false,
  is_admin: false,
  is_company: true,
  company_id: "company-a",
};

let currentUser: UserResponse = staffUser;

beforeEach(() => {
  currentUser = staffUser;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/user/me`, () =>
      HttpResponse.json(currentUser),
    ),
    http.get(`${testBackendUrl}/api/kp/latest`, () =>
      HttpResponse.json(testOpenEvent),
    ),
    http.get(`${testBackendUrl}/api/kp/list`, () =>
      HttpResponse.json([testOpenEvent]),
    ),
  );
});

const homeLink = () =>
  within(screen.getByRole("navigation", { hidden: true })).getByRole("link", {
    name: "nav.home",
  });

describe("the home page", () => {
  it.each([
    ["staff", staffUser],
    ["an admin", adminUser],
  ])(
    "shows %s the Kontaktparty dashboard without the banner",
    async (_, user) => {
      currentUser = user;

      renderWithProviders(<App />, { route: "/" });

      expect(
        await screen.findByText("kp.dashboard.title", {}, { timeout: 5000 }),
      ).toBeInTheDocument();
      expect(screen.queryByText("home.kp.title")).not.toBeInTheDocument();
      expect(homeLink()).toHaveAttribute("aria-current", "page");
    },
  );

  it("keeps the banner home page for a company", async () => {
    currentUser = companyUser;

    renderWithProviders(<App />, { route: "/" });

    expect(
      await screen.findByText("home.kp.title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.queryByText("kp.dashboard.title")).not.toBeInTheDocument();
    expect(homeLink()).toHaveAttribute("aria-current", "page");
  });
});
