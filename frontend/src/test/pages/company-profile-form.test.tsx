import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import CompanyProfileEdit from "../../pages/company/CompanyProfileEdit";
import { UserProvider } from "../../context/UserContext";
import type {
  CompanyProfileResponse,
  UserResponse,
} from "../../orval/generated/fastAPI.schemas";
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

const storedProfile: CompanyProfileResponse = {
  id: "profile-1",
  company_id: "company-1",
  description: "We build things.",
  website: "https://example.com",
  brand_name: "Examplify",
  general_email: "info@example.com",
  general_phone: "+41791234567",
  places_of_work: "Zurich",
  employee_count_switzerland: 42,
  employee_count_worldwide: 420,
  offers_internships: true,
  offers_part_time: false,
  offers_theses: true,
  offers_graduate_positions: false,
  languages: ["GERMAN", "ENGLISH"],
  billing_company_name: "Example AG",
  billing_street: "Bahnhofstrasse",
  billing_house_number: "1",
  billing_postal_code: "8001",
  billing_city: "Zurich",
  billing_country: "CH",
  billing_vat_number: "CHE-123.456.789",
  billing_email: "billing@example.com",
  shipping_address: "Example AG, Bahnhofstrasse 1, 8001 Zurich",
  kp_contact_user_id: "user-1",
  logo_url: null,
  industries: [{ id: "industry-1", name: "Software" }],
  profile_complete: true,
  missing_profile_fields: [],
};

const labelOf = (key: string) => new RegExp(`^${key.replaceAll(".", "\\.")}`);

let putBodies: unknown[] = [];
let memberRequests = 0;

const mockProfile = (profile: CompanyProfileResponse) => {
  server.use(
    http.get(`${testBackendUrl}/api/company/me/profile`, () =>
      HttpResponse.json(profile),
    ),
  );
};

const renderProfile = (
  user: UserResponse = companyUser,
  route = "/company/profile",
) =>
  renderWithProviders(
    <UserProvider user={user} isLoading={false}>
      <CompanyProfileEdit />
    </UserProvider>,
    { route },
  );

const backLinkHref = async () => {
  await screen.findByText("company_profile_form.title");
  return screen
    .getAllByRole("link")
    .find((link) => link.querySelector("svg.tabler-icon-arrow-back-up"))
    ?.getAttribute("href");
};

beforeEach(() => {
  putBodies = [];
  memberRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/industries`, () =>
      HttpResponse.json([{ id: "industry-1", name: "Software" }]),
    ),
    http.get(`${testBackendUrl}/api/company/me/members`, () => {
      memberRequests += 1;
      return HttpResponse.json([companyUser]);
    }),
    http.put(
      `${testBackendUrl}/api/company/me/profile`,
      async ({ request }) => {
        putBodies.push(await request.json());
        return HttpResponse.json(storedProfile);
      },
    ),
  );
  mockProfile(storedProfile);
});

describe("Company profile form", () => {
  it("renders the values stored on the server", async () => {
    renderProfile();

    expect(
      await screen.findByLabelText(labelOf("company_profile_form.brand_name")),
    ).toHaveValue("Examplify");
    expect(
      screen.getByLabelText(labelOf("company_profile_form.description")),
    ).toHaveValue("We build things.");
    expect(
      screen.getByLabelText(labelOf("company_profile_form.website")),
    ).toHaveValue("https://example.com");
    expect(
      screen.getByLabelText(
        labelOf("company_profile_form.employee_count_switzerland"),
      ),
    ).toHaveValue("42");
    expect(
      screen.getByLabelText(labelOf("company_profile_form.offers_internships")),
    ).toBeChecked();
    expect(
      screen.getByLabelText(labelOf("company_profile_form.offers_part_time")),
    ).not.toBeChecked();
    expect(
      screen.getByLabelText(labelOf("company_profile_form.billing_city")),
    ).toHaveValue("Zurich");

    const country = screen.getByRole("combobox", {
      name: labelOf("company_profile_form.billing_country"),
    });
    expect((country as HTMLInputElement).value).toContain("(CH)");
  });

  it("shows the missing mandatory fields as links to the inputs", async () => {
    mockProfile({
      ...storedProfile,
      description: "",
      billing_city: "",
      profile_complete: false,
      missing_profile_fields: ["description", "billing_city"],
    });

    renderProfile();

    expect(
      await screen.findByText("company_profile_form.missing_title"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "company_profile_form.description" }),
    ).toHaveAttribute("href", "#company-profile-description");
    expect(
      screen.getByRole("link", { name: "company_profile_form.billing_city" }),
    ).toHaveAttribute("href", "#company-profile-billing-city");
    expect(
      screen.getByText("company_profile_form.incomplete"),
    ).toBeInTheDocument();
  });

  it("does not submit without a contact person", async () => {
    mockProfile({
      ...storedProfile,
      kp_contact_user_id: null,
      profile_complete: false,
      missing_profile_fields: ["kp_contact_user_id"],
    });

    const { user } = renderProfile();

    expect(
      await screen.findByRole("link", {
        name: "company_profile_form.kp_contact_user",
      }),
    ).toHaveAttribute("href", "#company-profile-kp-contact-user-id");
    await user.click(
      screen.getByRole("button", { name: "company_profile_form.save" }),
    );

    expect(
      await screen.findByText("validation.required"),
    ).toBeInTheDocument();
    expect(putBodies).toHaveLength(0);
  });

  it("does not submit when the general email is invalid", async () => {
    const { user } = renderProfile();

    const email = await screen.findByLabelText(
      labelOf("company_profile_form.general_email"),
    );
    await user.clear(email);
    await user.paste("alice-at-example");
    await user.click(
      screen.getByRole("button", { name: "company_profile_form.save" }),
    );

    expect(
      await screen.findByText("validation.invalid_email"),
    ).toBeInTheDocument();
    expect(putBodies).toHaveLength(0);
  });

  it("does not submit when the billing country is missing", async () => {
    mockProfile({
      ...storedProfile,
      billing_country: "",
      profile_complete: false,
      missing_profile_fields: ["billing_country"],
    });

    const { user } = renderProfile();

    await user.click(
      await screen.findByRole("button", {
        name: "company_profile_form.save",
      }),
    );

    expect(
      await screen.findByText("company_profile_form.errors.country"),
    ).toBeInTheDocument();
    expect(putBodies).toHaveLength(0);
  });

  it("sends the complete profile payload", async () => {
    const { user } = renderProfile();

    const brandName = await screen.findByLabelText(
      labelOf("company_profile_form.brand_name"),
    );
    await user.clear(brandName);
    await user.paste("Examplify Group");
    await user.click(
      screen.getByRole("button", { name: "company_profile_form.save" }),
    );

    await waitFor(() => {
      expect(putBodies).toHaveLength(1);
    });
    expect(putBodies[0]).toEqual({
      description: "We build things.",
      website: "https://example.com",
      brand_name: "Examplify Group",
      general_email: "info@example.com",
      general_phone: "+41791234567",
      places_of_work: "Zurich",
      employee_count_switzerland: 42,
      employee_count_worldwide: 420,
      offers_internships: true,
      offers_part_time: false,
      offers_theses: true,
      offers_graduate_positions: false,
      languages: ["GERMAN", "ENGLISH"],
      industry_ids: ["industry-1"],
      kp_contact_user_id: "user-1",
      billing_company_name: "Example AG",
      billing_street: "Bahnhofstrasse",
      billing_house_number: "1",
      billing_postal_code: "8001",
      billing_city: "Zurich",
      billing_country: "CH",
      billing_vat_number: "CHE-123.456.789",
      billing_email: "billing@example.com",
      shipping_address: "Example AG, Bahnhofstrasse 1, 8001 Zurich",
    });
  });

  it("opens for a user the organisers have not confirmed yet", async () => {
    renderProfile({ ...companyUser, user_confirmed: false });

    expect(
      await screen.findByLabelText(labelOf("company_profile_form.brand_name")),
    ).toHaveValue("Examplify");
    expect(memberRequests).toBe(0);
  });

  it("goes back to the company overview by default", async () => {
    renderProfile();

    expect(await backLinkHref()).toBe("/company");
  });

  it("goes back to the page it was opened from", async () => {
    renderProfile(
      companyUser,
      `/company/profile?next=${encodeURIComponent("/kp/event-1/booking")}`,
    );

    expect(await backLinkHref()).toBe("/kp/event-1/booking");
  });
});
