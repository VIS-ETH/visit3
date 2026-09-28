import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../App";
import { server } from "./server";
import { testBackendUrl } from "./constants";
import { createToken } from "./jwt";
import { renderWithProviders } from "./render";

let meRequests = 0;

beforeEach(() => {
  meRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
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
