import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse, delay } from "msw";
import CompanyProfile from "../../pages/CompanyProfile";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { notificationsShow } from "../notifications";

const companyUser: UserResponse = {
  id: "user-1",
  email: "alice@example.com",
  first_name: "Alice",
  last_name: "Example",
  is_staff: false,
  is_admin: false,
  is_company: true,
  is_kp_president: false,
  email_confirmed: true,
  company_id: "company-1",
};

let memberRequests = 0;
let companyName = "Example AG";
let confirmedAt: string | null = "2026-01-01T00:00:00Z";
let companyStatus = 200;
let patchBodies: unknown[] = [];
let inviteBodies: unknown[] = [];

const renderOverview = () =>
  renderWithProviders(<CompanyProfile />, {
    route: "/company",
    currentUser: companyUser,
  });

const openSettings = async (
  user: ReturnType<typeof renderOverview>["user"],
) => {
  await screen.findByRole("heading", { name: "Example AG" });
  await user.click(
    screen.getByRole("button", { name: "company_profile.settings_button" }),
  );
  const dialog = await screen.findByRole("dialog");
  const input = within(dialog).getByLabelText("company_profile.name_label");
  return { dialog, input };
};

beforeEach(() => {
  memberRequests = 0;
  companyName = "Example AG";
  confirmedAt = "2026-01-01T00:00:00Z";
  companyStatus = 200;
  patchBodies = [];
  inviteBodies = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/user/profile`, () =>
      HttpResponse.json({
        ...companyUser,
        company: { id: "company-1", name: companyName },
      }),
    ),
    http.get(`${testBackendUrl}/api/company/me`, () =>
      companyStatus === 200
        ? HttpResponse.json({
            id: "company-1",
            name: companyName,
            confirmed_at: confirmedAt,
            profile_complete: false,
            missing_profile_fields: ["description", "billing_city"],
          })
        : HttpResponse.json(
            { code: "error.internal", message: "boom" },
            { status: companyStatus },
          ),
    ),
    http.get(`${testBackendUrl}/api/company/me/members`, () => {
      memberRequests += 1;
      return HttpResponse.json([companyUser]);
    }),
    http.patch(`${testBackendUrl}/api/company/me`, async ({ request }) => {
      const body = (await request.json()) as { name: string };
      patchBodies.push(body);
      companyName = body.name;
      confirmedAt = null;
      return HttpResponse.json({ id: "company-1", name: companyName });
    }),
    http.post(`${testBackendUrl}/api/company/invite`, async ({ request }) => {
      inviteBodies.push(await request.json());
      await delay(300);
      return HttpResponse.json({});
    }),
  );
});

describe("Company overview", () => {
  it("links to the profile and shows the completeness state", async () => {
    renderOverview();

    expect(await screen.findByText("Example AG")).toBeInTheDocument();
    expect(
      await screen.findByText("company_profile_form.incomplete"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("company_profile.profile_incomplete_hint"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "company_profile.profile_link" }),
    ).toHaveAttribute("href", "/company/profile");
    expect(await screen.findByText("alice@example.com")).toBeInTheDocument();
    expect(
      screen.queryByText("company_profile.unconfirmed_description"),
    ).not.toBeInTheDocument();
  });

  it("flags a company the organisers have not confirmed yet", async () => {
    confirmedAt = null;
    renderOverview();

    expect(
      await screen.findByText("company_profile.unconfirmed_description"),
    ).toBeInTheDocument();
    expect(await screen.findByText("alice@example.com")).toBeInTheDocument();
    expect(memberRequests).toBe(1);
  });

  it("does not claim missing fields when the company fails to load", async () => {
    companyStatus = 500;
    renderOverview();

    expect(
      await screen.findByRole("heading", { name: "Example AG" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("error.load_failed")).toBeInTheDocument();
    expect(
      screen.queryByText("company_profile.profile_incomplete_hint"),
    ).not.toBeInTheDocument();
  });
});

describe("Company settings", () => {
  it("shows the new name and the confirmation notice after a rename", async () => {
    const { user } = renderOverview();
    const { dialog, input } = await openSettings(user);

    await user.clear(input);
    await user.type(input, "Renamed AG");
    await user.click(
      within(dialog).getByRole("button", { name: "company_profile.save" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Renamed AG" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("company_profile.unconfirmed_title"),
    ).toBeInTheDocument();
    expect(patchBodies).toEqual([{ name: "Renamed AG" }]);
  });

  it("does not accept a whitespace-only name", async () => {
    const { user } = renderOverview();
    const { dialog, input } = await openSettings(user);

    await user.clear(input);
    await user.type(input, "   ");

    expect(
      within(dialog).getByRole("button", { name: "company_profile.save" }),
    ).toBeDisabled();
  });
});

describe("Company invites", () => {
  it("keeps text typed while an invite is sending", async () => {
    const { user } = renderOverview();
    const field = await screen.findByLabelText("company_profile.invite_email");
    await waitFor(() => expect(field).toBeEnabled());
    await user.type(field, "bob@example.com");
    await user.click(
      screen.getByRole("button", { name: "company_profile.invite_button" }),
    );
    await user.clear(field);
    await user.type(field, "carol@example.com");

    await waitFor(() =>
      expect(notificationsShow).toHaveBeenCalledWith(
        expect.objectContaining({ message: "company_profile.invite_success" }),
      ),
    );
    expect(inviteBodies).toEqual([{ email: "bob@example.com" }]);
    expect(field).toHaveValue("carol@example.com");
  });

  it("disables invites until the company is confirmed", async () => {
    confirmedAt = null;
    renderOverview();

    expect(
      await screen.findByText("company_profile.invite_unconfirmed"),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("company_profile.invite_email"),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "company_profile.invite_button" }),
    ).toBeDisabled();
  });
});
