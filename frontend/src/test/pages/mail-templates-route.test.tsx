import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../../App";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testMailPreview, testMailTemplate } from "../fixtures/mail-template";

const mailTemplatesRoute = "/admin/mail-templates";

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

const companyUser: UserResponse = {
  ...staffUser,
  id: "company-1",
  email: "company@example.com",
  is_staff: false,
  is_company: true,
  company_id: "company-1",
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
    http.get(`${testBackendUrl}/api/mail-templates`, () =>
      HttpResponse.json([testMailTemplate]),
    ),
    http.get(`${testBackendUrl}/api/mail-templates/:key`, () =>
      HttpResponse.json(testMailTemplate),
    ),
    http.post(`${testBackendUrl}/api/mail-templates/:key/preview`, () =>
      HttpResponse.json(testMailPreview),
    ),
  );
});

describe("the mail templates route", () => {
  it("links the page from the staff navigation", async () => {
    mockCurrentUser(staffUser);

    renderWithProviders(<App />, { route: mailTemplatesRoute });

    const link = await screen.findByRole(
      "link",
      { name: "nav.mail_templates" },
      { timeout: 5000 },
    );
    expect(link).toHaveAttribute("href", mailTemplatesRoute);
  });

  it("opens the page for staff", async () => {
    mockCurrentUser(staffUser);

    renderWithProviders(<App />, { route: mailTemplatesRoute });

    expect(
      await screen.findByText("mail_templates.title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  it("sends a company user to the explanation page", async () => {
    mockCurrentUser(companyUser);

    renderWithProviders(<App />, { route: mailTemplatesRoute });

    expect(
      await screen.findByText("not_allowed.title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.queryByText("mail_templates.title")).not.toBeInTheDocument();
  });
});
