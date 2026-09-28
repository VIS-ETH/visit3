import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import CompanyProfile from "../../pages/CompanyProfile";
import { UserProvider } from "../../context/UserContext";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";

const companyUser: UserResponse = {
  id: "user-1",
  email: "alice@example.com",
  first_name: "Alice",
  last_name: "Example",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  user_confirmed: true,
  email_confirmed: true,
  company_id: "company-1",
};

let memberRequests = 0;

const renderOverview = (user: UserResponse) =>
  renderWithProviders(
    <UserProvider user={user} isLoading={false}>
      <CompanyProfile />
    </UserProvider>,
    { route: "/company" },
  );

beforeEach(() => {
  memberRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/user/profile`, () =>
      HttpResponse.json({
        ...companyUser,
        company: { id: "company-1", name: "Example AG" },
      }),
    ),
    http.get(`${testBackendUrl}/api/company/me`, () =>
      HttpResponse.json({
        id: "company-1",
        name: "Example AG",
        profile_complete: false,
        missing_profile_fields: ["description", "billing_city"],
      }),
    ),
    http.get(`${testBackendUrl}/api/company/me/members`, () => {
      memberRequests += 1;
      return HttpResponse.json([companyUser]);
    }),
  );
});

describe("Company overview", () => {
  it("links to the profile and shows the completeness state", async () => {
    renderOverview(companyUser);

    expect(await screen.findByText("Example AG")).toBeInTheDocument();
    expect(
      screen.getByText("company_profile_form.incomplete"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("company_profile.profile_incomplete_hint"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "company_profile.profile_link" }),
    ).toHaveAttribute("href", "/company/profile");
    expect(await screen.findByText("alice@example.com")).toBeInTheDocument();
  });

  it("waits for the organisers before showing members", async () => {
    renderOverview({ ...companyUser, user_confirmed: false });

    expect(await screen.findByText("user.unconfirmed")).toBeInTheDocument();
    expect(
      screen.getByText("company_profile.members_unconfirmed"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "company_profile.profile_link" }),
    ).toBeInTheDocument();
    expect(memberRequests).toBe(0);
  });
});
