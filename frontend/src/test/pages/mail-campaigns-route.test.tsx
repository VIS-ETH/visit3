import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../../App";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testCampaignEvent } from "../fixtures/mail-campaign";

const route = "/admin/mail-campaigns";

const staffUser: UserResponse = {
  id: "staff-1",
  email: "staff@example.com",
  is_staff: true,
  is_admin: false,
  is_company: false,
  is_kp_president: false,
  user_confirmed: true,
  email_confirmed: true,
};

const presidentUser: UserResponse = {
  ...staffUser,
  id: "president-1",
  email: "president@example.com",
  is_kp_president: true,
};

const mockCurrentUser = (user: UserResponse) => {
  server.use(
    http.get(`${testBackendUrl}/api/user/me`, () => HttpResponse.json(user)),
  );
};

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.post(`${testBackendUrl}/api/auth/refresh`, () =>
      HttpResponse.json({ access_token: createToken(3600) }),
    ),
    http.get(`${testBackendUrl}/api/kp/list`, () =>
      HttpResponse.json([testCampaignEvent]),
    ),
    http.get(`${testBackendUrl}/api/kp/latest`, () =>
      HttpResponse.json(testCampaignEvent),
    ),
    http.get(`${testBackendUrl}/api/mail-campaigns`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/mail-campaigns/variables`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/mail-campaigns/companies`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/booth-zones`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/mail-templates`, () =>
      HttpResponse.json([]),
    ),
    http.post(`${testBackendUrl}/api/mail-campaigns/audience`, () =>
      HttpResponse.json({
        recipient_count: 0,
        skipped_count: 0,
        recipients: [],
      }),
    ),
  );
});

describe("the mail campaigns route", () => {
  it("is linked and opened for the Kontaktparty organisers", async () => {
    mockCurrentUser(presidentUser);

    renderWithProviders(<App />, { route });

    const link = await screen.findByRole(
      "link",
      { name: "nav.mail_campaigns" },
      { timeout: 5000 },
    );
    expect(link).toHaveAttribute("href", route);
    expect(
      await screen.findByText("mail_campaigns.title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  it("sends staff without the organiser role away", async () => {
    mockCurrentUser(staffUser);

    renderWithProviders(<App />, { route });

    expect(
      await screen.findByText("not_allowed.title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.queryByText("mail_campaigns.title")).not.toBeInTheDocument();
  });

  it("hides the link from staff without the organiser role", async () => {
    mockCurrentUser(staffUser);

    renderWithProviders(<App />, { route: "/admin/mail-templates" });

    expect(
      await screen.findByRole(
        "link",
        { name: "nav.mail_templates" },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.queryByRole("link", { name: "nav.mail_campaigns" }),
      ).not.toBeInTheDocument();
    });
  });
});
