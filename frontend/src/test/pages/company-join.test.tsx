import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import CompanyJoin from "../../pages/CompanyJoin";
import { UserProvider } from "../../context/UserContext";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { companyUser } from "../fixtures/users";
import { createToken } from "../jwt";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { renderWithProviders } from "../render";

const inviteToken = "invite-token";
const joinRoute = `/company/join/${inviteToken}`;

let registerBodies: unknown[] = [];

const mockInvite = (accountExists: boolean) => {
  server.use(
    http.get(`${testBackendUrl}/api/company/invite/:token`, () =>
      HttpResponse.json({
        company_name: "Example AG",
        account_exists: accountExists,
      }),
    ),
  );
};

const renderJoin = (currentUser?: UserResponse) =>
  renderWithProviders(
    <UserProvider user={currentUser} isLoading={false}>
      <Routes>
        <Route path="/company/join/:token" element={<CompanyJoin />} />
        <Route path="/company" element={<p data-testid="company-page" />} />
      </Routes>
    </UserProvider>,
    { route: joinRoute },
  );

beforeEach(() => {
  registerBodies = [];
  server.use(
    http.post(`${testBackendUrl}/api/auth/refresh`, () =>
      HttpResponse.json({}, { status: 401 }),
    ),
    http.post(`${testBackendUrl}/api/auth/register`, async ({ request }) => {
      registerBodies.push(await request.json());
      return HttpResponse.json({ id: "user-2", email: "bob@example.com" });
    }),
  );
});

describe("Company invite landing", () => {
  it("sends an existing account to the login page", async () => {
    mockInvite(true);

    renderJoin();

    const loginLink = await screen.findByRole("link", {
      name: "company_join.log_in",
    });
    expect(loginLink).toHaveAttribute(
      "href",
      `/login?next=${encodeURIComponent(joinRoute)}`,
    );
    expect(
      screen.queryByLabelText("register.first_name"),
    ).not.toBeInTheDocument();
  });

  it("offers the signup form when the invited account does not exist", async () => {
    mockInvite(false);

    renderJoin();

    expect(await screen.findByText("register.invite.hint")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "company_join.log_in" }),
    ).not.toBeInTheDocument();
  });

  it("registers the invited account with the invite token", async () => {
    mockInvite(false);

    const { user } = renderJoin();

    const firstName = await screen.findByLabelText(/^register\.first_name/);
    await user.click(firstName);
    await user.paste("Bob");
    await user.click(screen.getByLabelText(/^register\.last_name/));
    await user.paste("Builder");
    await user.click(screen.getByLabelText(/^email\.title/));
    await user.paste("bob@example.com");
    await user.click(screen.getByLabelText(/^register\.password\.title/));
    await user.paste("supersecret1");
    await user.click(screen.getByLabelText(/^register\.password\.confirm/));
    await user.paste("supersecret1");
    await user.click(
      screen.getByRole("button", { name: "register.invite.submit" }),
    );

    await waitFor(() => {
      expect(registerBodies).toHaveLength(1);
    });
    expect(registerBodies[0]).toEqual({
      email: "bob@example.com",
      password: "supersecret1",
      first_name: "Bob",
      last_name: "Builder",
      phone_number: "",
      invite_token: inviteToken,
    });
    expect(
      await screen.findByText("register.success.alert"),
    ).toBeInTheDocument();
  });

  it("explains that an invite has expired", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/company/invite/:token`, () =>
        HttpResponse.json(
          { code: "error.invite_expired", statusCode: 400 },
          { status: 400 },
        ),
      ),
    );

    renderJoin();

    expect(await screen.findByText("error.invite_expired")).toBeInTheDocument();
  });

  it("shows a server error instead of a missing invite when loading fails", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/company/invite/:token`, () =>
        HttpResponse.json(
          { statusCode: 500, code: "error.internal", message: "boom" },
          { status: 500 },
        ),
      ),
    );

    renderJoin();

    expect(await screen.findByText("error.load_failed")).toBeInTheDocument();
    expect(
      screen.queryByText("error.invite_not_found"),
    ).not.toBeInTheDocument();
  });
});

describe("Company invite for a signed-in user", () => {
  const memberOf = (companyId: string): UserResponse => ({
    ...companyUser,
    company_id: companyId,
  });

  beforeEach(() => {
    localStorage.setItem("token", createToken(3600));
  });

  it("explains that the user already belongs to another company", async () => {
    mockInvite(true);
    server.use(
      http.post(`${testBackendUrl}/api/company/invite/:token/accept`, () =>
        HttpResponse.json(
          { statusCode: 403, code: "error.not_allowed", message: "no" },
          { status: 403 },
        ),
      ),
    );

    const { user } = renderJoin(memberOf("other-company"));
    await user.click(
      await screen.findByRole("button", { name: "company_join.button" }),
    );

    expect(
      await screen.findByText("company_join.already_in_company"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("error.invite_not_found"),
    ).not.toBeInTheDocument();
  });

  it("opens the company when the invite was already accepted", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/company/invite/:token`, () =>
        HttpResponse.json(
          { statusCode: 404, code: "error.invite_not_found", message: "gone" },
          { status: 404 },
        ),
      ),
    );

    renderJoin(memberOf("example-ag"));

    expect(await screen.findByTestId("company-page")).toBeInTheDocument();
  });
});
