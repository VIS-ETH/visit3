import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../App";
import { server } from "./server";
import { testBackendUrl } from "./constants";
import { createToken } from "./jwt";
import { renderWithProviders } from "./render";
import { getToken } from "../api/utils";
import { rememberLoginNext } from "../utils/navigation";

let requestOrder: string[] = [];

const currentUser = {
  id: "user-1",
  email: "ada@example.com",
  first_name: "Ada",
  last_name: "Lovelace",
  is_admin: false,
  is_staff: false,
  is_company: true,
  is_kp_president: false,
  email_confirmed: true,
  company: null,
  roles: [],
};

const refusedRefresh = () =>
  http.post(`${testBackendUrl}/api/auth/refresh`, () => {
    requestOrder.push("refresh");
    return HttpResponse.json({ detail: "no" }, { status: 401 });
  });

beforeEach(() => {
  requestOrder = [];
  localStorage.clear();
  sessionStorage.clear();
  server.use(
    http.post(`${testBackendUrl}/api/auth/refresh`, () => {
      requestOrder.push("refresh");
      localStorage.setItem("token", createToken(3600));
      return HttpResponse.json({ access_token: createToken(3600) });
    }),
    http.get(`${testBackendUrl}/api/user/me`, () => {
      requestOrder.push("me");
      return HttpResponse.json(currentUser);
    }),
  );
});

describe("App without an access token in storage", () => {
  it("fetches an access token before it loads the current user", async () => {
    renderWithProviders(<App />);

    await waitFor(() => expect(requestOrder).toContain("me"), {
      timeout: 5000,
    });

    expect(requestOrder[0]).toBe("refresh");
  });
});

describe("App deep links", () => {
  it("keeps a logged-out deep link as next on the login", async () => {
    server.use(refusedRefresh());
    renderWithProviders(<App />, { route: "/kp/event-1/booking" });

    const register = await screen.findByRole(
      "link",
      { name: "login.register.title" },
      { timeout: 5000 },
    );
    expect(register).toHaveAttribute(
      "href",
      `/register?next=${encodeURIComponent("/kp/event-1/booking")}`,
    );
  });

  it("opens the page requested before a Keycloak sign-in", async () => {
    rememberLoginNext("/profile");
    server.use(
      http.get(`${testBackendUrl}/api/user/me`, () =>
        HttpResponse.json({ ...currentUser, company_id: "company-1" }),
      ),
      http.get(`${testBackendUrl}/api/user/profile`, () =>
        HttpResponse.json({ id: "user-1", email: "ada@example.com" }),
      ),
    );
    renderWithProviders(<App />);

    expect(
      await screen.findByRole(
        "heading",
        { name: "profile.title" },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
  });
});

describe("App after a logout", () => {
  it("does not sign back in when the logout request failed", async () => {
    localStorage.setItem("token", createToken(3600));
    server.use(
      http.post(`${testBackendUrl}/api/user/logout`, () =>
        HttpResponse.json(
          { statusCode: 500, code: "error.internal" },
          { status: 500 },
        ),
      ),
    );
    const { user } = renderWithProviders(<App />, { route: "/setup-company" });

    await user.click(
      await screen.findByRole(
        "button",
        { name: "nav.logout" },
        { timeout: 5000 },
      ),
    );
    await user.click(
      await screen.findByRole("button", { name: "nav.logout_confirm_submit" }),
    );

    expect(
      await screen.findByRole("heading", { name: "company.login" }),
    ).toBeInTheDocument();
    expect(getToken()).toBeNull();
    expect(requestOrder).not.toContain("refresh");
  });
});
