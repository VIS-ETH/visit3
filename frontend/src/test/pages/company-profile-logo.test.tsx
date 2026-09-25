import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { File as NodeFile } from "node:buffer";
import CompanyProfileEdit from "../../pages/company/CompanyProfileEdit";
import { UserProvider } from "../../context/UserContext";
import type {
  CompanyProfileResponse,
  UserResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { installBookletPageHandler } from "../fixtures/company-profile";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";

const companyUser: UserResponse = {
  id: "user-1",
  email: "alice@example.com",
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
  kp_contact_user_id: "user-1",
  billing_company_name: "Example AG",
  billing_street: "Bahnhofstrasse",
  billing_postal_code: "8001",
  billing_city: "Zurich",
  billing_country: "CH",
  billing_email: "billing@example.com",
  logo_url: null,
  industries: [],
  languages: [],
  profile_complete: true,
  missing_profile_fields: [],
};

const uploadedLogoUrl = "https://files.example.com/logo.png";

interface LogoUpload {
  hasFileField: boolean;
  contentType: string;
}

let logoUploads: LogoUpload[] = [];

const createLogoFile = () =>
  new NodeFile(["logo-bytes"], "logo.png", {
    type: "image/png",
  }) as unknown as File;

beforeEach(() => {
  logoUploads = [];
  localStorage.setItem("token", createToken(3600));
  installBookletPageHandler();
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/industries`, () => HttpResponse.json([])),
    http.get(`${testBackendUrl}/api/company/me/members`, () =>
      HttpResponse.json([companyUser]),
    ),
    http.get(`${testBackendUrl}/api/company/me/profile`, () =>
      HttpResponse.json(storedProfile),
    ),
    http.post(
      `${testBackendUrl}/api/company/me/profile/logo`,
      async ({ request }) => {
        const contentType = request.headers.get("content-type") ?? "";
        const body = await request.formData();
        logoUploads.push({ hasFileField: body.has("file"), contentType });
        return HttpResponse.json({
          ...storedProfile,
          logo_url: uploadedLogoUrl,
        });
      },
    ),
  );
});

const renderProfileEdit = () =>
  renderWithProviders(
    <UserProvider user={companyUser} isLoading={false}>
      <CompanyProfileEdit />
    </UserProvider>,
    { route: "/company/profile" },
  );

describe("Company logo upload", () => {
  it("posts the chosen file as multipart form data", async () => {
    const { user, container } = renderWithProviders(
      <UserProvider user={companyUser} isLoading={false}>
        <CompanyProfileEdit />
      </UserProvider>,
      { route: "/company/profile" },
    );

    await screen.findByText("company_profile_form.logo");
    const fileInput =
      container.querySelector<HTMLInputElement>('input[type="file"]');
    expect(fileInput).not.toBeNull();

    await user.upload(fileInput!, createLogoFile());

    await waitFor(() => {
      expect(logoUploads).toHaveLength(1);
    });
    expect(logoUploads[0].hasFileField).toBe(true);
    expect(logoUploads[0].contentType).toContain("multipart/form-data");
    expect(
      await screen.findByAltText("company_profile_form.logo_alt"),
    ).toHaveAttribute("src", uploadedLogoUrl);
  });

  it("retries the upload when the same file is picked again after a failure", async () => {
    let attempts = 0;
    server.use(
      http.post(`${testBackendUrl}/api/company/me/profile/logo`, () => {
        attempts += 1;
        return HttpResponse.json({ detail: "storage down" }, { status: 500 });
      }),
    );
    const { user, container } = renderProfileEdit();

    await screen.findByText("company_profile_form.logo");
    const fileInput =
      container.querySelector<HTMLInputElement>('input[type="file"]');
    const logo = createLogoFile();

    await user.upload(fileInput!, logo);
    await waitFor(() => expect(attempts).toBe(1));
    await user.upload(fileInput!, logo);

    await waitFor(() => expect(attempts).toBe(2));
  });
});
