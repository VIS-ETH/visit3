import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../App";
import { server } from "./server";
import { testBackendUrl } from "./constants";
import { createToken } from "./jwt";
import { renderWithProviders } from "./render";
import { isImpersonating, setImpersonation } from "../api/utils";
import { stubLocation } from "./location";

let meRequests = 0;

beforeEach(() => {
  meRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.post(`${testBackendUrl}/api/auth/refresh`, () =>
      HttpResponse.json({ access_token: createToken(3600) }),
    ),
    http.get(`${testBackendUrl}/api/user/me`, () => {
      meRequests += 1;
      return HttpResponse.json(
        { statusCode: 500, code: "server.error" },
        { status: 500 },
      );
    }),
  );
});

describe("App with a failing current user request", () => {
  it("shows a retryable error instead of the login page", async () => {
    const { user } = renderWithProviders(<App />);

    expect(
      await screen.findByText(
        "error.session_load_failed",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "company.login" }),
    ).not.toBeInTheDocument();

    const requestsBeforeRetry = meRequests;
    await user.click(screen.getByRole("button", { name: "error.retry" }));

    await waitFor(() => {
      expect(meRequests).toBeGreaterThan(requestsBeforeRetry);
    });
  });
});

describe("App with a refused impersonation", () => {
  it("offers to stop impersonating", async () => {
    setImpersonation("admin-2", "Other Admin", "/user-management");
    server.use(
      http.get(`${testBackendUrl}/api/user/me`, () =>
        HttpResponse.json(
          { statusCode: 403, code: "error.not_allowed" },
          { status: 403 },
        ),
      ),
    );
    const location = stubLocation("/");
    const { user } = renderWithProviders(<App />);

    await user.click(
      await screen.findByRole(
        "button",
        { name: "impersonation.stop" },
        { timeout: 5000 },
      ),
    );

    expect(isImpersonating()).toBe(false);
    location.restore();
  });
});
