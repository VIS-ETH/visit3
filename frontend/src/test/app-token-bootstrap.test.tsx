import { beforeEach, describe, expect, it } from "vitest";
import { waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../App";
import { server } from "./server";
import { testBackendUrl } from "./constants";
import { createToken } from "./jwt";
import { renderWithProviders } from "./render";

let requestOrder: string[] = [];

beforeEach(() => {
  requestOrder = [];
  localStorage.clear();
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.post(`${testBackendUrl}/api/auth/refresh`, () => {
      requestOrder.push("refresh");
      localStorage.setItem("token", createToken(3600));
      return HttpResponse.json({ access_token: createToken(3600) });
    }),
    http.get(`${testBackendUrl}/api/user/me`, () => {
      requestOrder.push("me");
      return HttpResponse.json({
        id: "user-1",
        email: "ada@example.com",
        first_name: "Ada",
        last_name: "Lovelace",
        is_admin: false,
        is_staff: false,
        is_company: true,
        is_kp_president: false,
        user_confirmed: true,
        email_confirmed: true,
        company: null,
        roles: [],
      });
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
