import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../../App";
import { setToken } from "../../api/utils";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";

let confirmed = false;

beforeEach(() => {
  confirmed = false;
  setToken(createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/user/me`, () =>
      HttpResponse.json({
        id: "user-1",
        email: "user@example.com",
        is_staff: false,
        is_admin: false,
        is_company: true,
        is_kp_president: false,
        company_id: "company-1",
        email_confirmed: confirmed,
      }),
    ),
    http.get(`${testBackendUrl}/api/user/confirm-email/:token`, () =>
      HttpResponse.json(true),
    ),
    http.post(`${testBackendUrl}/api/user/confirm-email/:token`, () => {
      confirmed = true;
      return new HttpResponse(null, { status: 200 });
    }),
  );
});

describe("confirming the email while signed in", () => {
  it("lets the user into the confirmed pages right away", async () => {
    const { user } = renderWithProviders(<App />, {
      route: "/confirm-email/tok",
    });

    await user.click(
      await screen.findByRole(
        "button",
        { name: "email.confirm.confirm_button" },
        { timeout: 5000 },
      ),
    );
    await screen.findByText("email.confirm.success");
    await user.click(screen.getByRole("button", { name: "nav.home" }));

    await waitFor(() =>
      expect(
        screen.queryByText("email.confirm.success"),
      ).not.toBeInTheDocument(),
    );
    expect(
      screen.queryByText("email.confirm.unconfirmed"),
    ).not.toBeInTheDocument();
  });
});
