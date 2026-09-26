import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { File as NodeFile } from "node:buffer";
import { Route, Routes } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import { UserProvider } from "../../context/UserContext";
import type { CompanyProfileResponse } from "../../orval/generated/fastAPI.schemas";
import CompanyProfileAdmin from "../../pages/admin/CompanyProfileAdmin";
import { testBackendUrl } from "../constants";
import {
  acmeCompany,
  adminUser,
  memberUser,
  softwareIndustry,
} from "../fixtures/admin";
import {
  installBookletPageHandler,
  type BookletPageRequest,
} from "../fixtures/company-profile";
import { createToken } from "../jwt";
import { SLOW_WAIT } from "../timeouts";
import { renderWithProviders } from "../render";
import { server } from "../server";

const storedProfile: CompanyProfileResponse = {
  id: "profile-1",
  company_id: acmeCompany.id,
  description: "<p>We build booths.</p>",
  website: "https://acme.test",
  brand_name: "Acme",
  general_email: "contact@acme.test",
  general_phone: "+41441111111",
  places_of_work: "Zurich",
  employee_count_switzerland: 10,
  employee_count_worldwide: 20,
  offers_internships: true,
  offers_part_time: false,
  offers_theses: false,
  offers_graduate_positions: false,
  languages: ["GERMAN"],
  billing_company_name: "Acme AG",
  billing_street: "Bahnhofstrasse",
  billing_house_number: "1",
  billing_postal_code: "8001",
  billing_city: "Zurich",
  billing_country: "CH",
  billing_vat_number: "CHE-123.456.789",
  billing_email: "billing@acme.test",
  kp_contact_user_id: memberUser.id,
  logo_url: null,
  industries: [softwareIndustry],
  profile_complete: true,
  missing_profile_fields: [],
};

const uploadedLogoUrl = "https://files.example.com/acme-logo.png";

let profileRequests: string[] = [];
let putCalls: { companyId: string; body: unknown }[] = [];
let logoUploads: { companyId: string; hasFileField: boolean }[] = [];
let logoDeletes: string[] = [];
let bookletRequests: BookletPageRequest[] = [];

beforeEach(() => {
  profileRequests = [];
  putCalls = [];
  logoUploads = [];
  logoDeletes = [];
  localStorage.setItem("token", createToken(3600));

  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(
      `${testBackendUrl}/api/company/:companyId/profile`,
      ({ params }) => {
        profileRequests.push(String(params.companyId));
        return HttpResponse.json(storedProfile);
      },
    ),
    http.put(
      `${testBackendUrl}/api/company/:companyId/profile`,
      async ({ params, request }) => {
        putCalls.push({
          companyId: String(params.companyId),
          body: await request.json(),
        });
        return HttpResponse.json(storedProfile);
      },
    ),
    http.post(
      `${testBackendUrl}/api/company/:companyId/profile/logo`,
      async ({ params, request }) => {
        const body = await request.formData();
        logoUploads.push({
          companyId: String(params.companyId),
          hasFileField: body.has("file"),
        });
        return HttpResponse.json({
          ...storedProfile,
          logo_url: uploadedLogoUrl,
        });
      },
    ),
    http.delete(
      `${testBackendUrl}/api/company/:companyId/profile/logo`,
      ({ params }) => {
        logoDeletes.push(String(params.companyId));
        return HttpResponse.json({ ...storedProfile, logo_url: null });
      },
    ),
    http.get(`${testBackendUrl}/api/company/:companyId/users`, () =>
      HttpResponse.json([memberUser]),
    ),
    http.get(`${testBackendUrl}/api/industries`, () =>
      HttpResponse.json([softwareIndustry]),
    ),
  );
  bookletRequests = installBookletPageHandler();
});

const renderPage = () =>
  renderWithProviders(
    <UserProvider user={adminUser} isLoading={false}>
      <Routes>
        <Route
          path="/company-management/:companyId/profile"
          element={<CompanyProfileAdmin />}
        />
      </Routes>
    </UserProvider>,
    { route: `/company-management/${acmeCompany.id}/profile` },
  );

describe("the staff company profile page", () => {
  it("loads the profile of the company in the route", async () => {
    renderPage();

    expect(
      await screen.findByDisplayValue(storedProfile.brand_name ?? ""),
    ).toBeInTheDocument();
    expect(profileRequests).toEqual([acmeCompany.id]);
  });

  it("saves the profile through the staff endpoint", async () => {
    const { user } = renderPage();
    const brandName = await screen.findByDisplayValue(
      storedProfile.brand_name ?? "",
    );

    await user.clear(brandName);
    await user.type(brandName, "Acme Robotics");
    await user.click(
      screen.getByRole("button", { name: "company_profile_form.save" }),
    );

    await waitFor(() => {
      expect(putCalls).toHaveLength(1);
    });
    expect(putCalls[0].companyId).toBe(acmeCompany.id);
    expect(putCalls[0].body).toMatchObject({
      brand_name: "Acme Robotics",
      industry_ids: [softwareIndustry.id],
      kp_contact_user_id: memberUser.id,
    });
  });

  it("uploads and removes the logo through the staff endpoints", async () => {
    const { user, container } = renderPage();
    await screen.findByText("company_profile_form.logo");
    const fileInput =
      container.querySelector<HTMLInputElement>('input[type="file"]');
    expect(fileInput).not.toBeNull();

    await user.upload(
      fileInput!,
      new NodeFile(["logo-bytes"], "logo.png", {
        type: "image/png",
      }) as unknown as File,
    );

    await waitFor(() => {
      expect(logoUploads).toHaveLength(1);
    });
    expect(logoUploads[0]).toEqual({
      companyId: acmeCompany.id,
      hasFileField: true,
    });
    expect(
      await screen.findByAltText("company_profile_form.logo_alt"),
    ).toHaveAttribute("src", uploadedLogoUrl);

    await user.click(
      screen.getByRole("button", { name: "company_profile_form.logo_remove" }),
    );

    await waitFor(() => {
      expect(logoDeletes).toEqual([acmeCompany.id]);
    });
    await waitFor(() => {
      expect(
        screen.queryByAltText("company_profile_form.logo_alt"),
      ).not.toBeInTheDocument();
    });
  });
});

describe("the staff booklet page", () => {
  it("renders the page of the company in the route", async () => {
    renderPage();

    expect(
      await screen.findByRole(
        "img",
        { name: "company_profile_form.booklet_page_alt" },
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
    expect(bookletRequests[0].url).toBe(
      `${testBackendUrl}/api/company/${acmeCompany.id}/profile/booklet-page`,
    );
    expect(bookletRequests[0].body).toMatchObject({ brand_name: "Acme" });
  });
});
