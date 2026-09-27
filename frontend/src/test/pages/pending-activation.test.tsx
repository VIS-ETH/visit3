import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../../App";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";

const pendingUser: UserResponse = {
  id: "pending-1",
  email: "grace.hopper@ethz.ch",
  first_name: "Grace",
  last_name: "Hopper",
  is_staff: false,
  is_admin: false,
  is_company: false,
  is_kp_president: false,
  user_confirmed: true,
  email_confirmed: true,
};

let currentUser: UserResponse = pendingUser;

beforeEach(() => {
  currentUser = pendingUser;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/user/me`, () =>
      HttpResponse.json(currentUser),
    ),
    http.get(`${testBackendUrl}/api/kp/latest`, () => HttpResponse.json(null)),
  );
});

describe("an account waiting for activation", () => {
  it.each(["/", "/kp", "/profile", "/user-management"])(
    "shows the waiting notice and logout on %s",
    async (route) => {
      renderWithProviders(<App />, { route });

      expect(
        await screen.findByText(
          "user.pending_activation",
          {},
          { timeout: 5000 },
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "nav.logout" }),
      ).toBeInTheDocument();
      expect(screen.queryByText("not_allowed.title")).not.toBeInTheDocument();
    },
  );

  it("opens the portal once an admin granted staff", async () => {
    currentUser = { ...pendingUser, is_staff: true };

    renderWithProviders(<App />, { route: "/" });

    expect(
      await screen.findByText("home.kp.title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("user.pending_activation"),
    ).not.toBeInTheDocument();
  });
});
