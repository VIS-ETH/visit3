import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import CompanyJoin from "../../pages/CompanyJoin";
import { UserProvider } from "../../context/UserContext";
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

const renderJoin = () =>
  renderWithProviders(
    <UserProvider user={undefined} isLoading={false}>
      <Routes>
        <Route path="/company/join/:token" element={<CompanyJoin />} />
      </Routes>
    </UserProvider>,
    { route: joinRoute },
  );

beforeEach(() => {
  registerBodies = [];
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
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
});
