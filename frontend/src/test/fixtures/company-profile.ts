import { screen } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type {
  BookletPageResponse,
  CompanyProfileResponse,
  MyCompanyResponse,
} from "../../orval/generated/fastAPI.schemas";
import { testBackendUrl } from "../constants";
import { server } from "../server";
import { SLOW_WAIT } from "../timeouts";

export const testCompany: MyCompanyResponse = {
  id: "99999999-9999-9999-9999-999999999999",
  name: "Acme AG",
  profile_complete: true,
  profile_bookable: true,
  missing_profile_fields: [],
};

export const testCompanyProfile: CompanyProfileResponse = {
  company_id: testCompany.id,
  description: "We build reliable booths",
  brand_name: "Acme Robotics",
  general_email: "info@acme.test",
  general_phone: "+41 44 000 00 00",
  kp_contact_user_id: "user-1",
  kp_contact_user: {
    id: "user-1",
    email: "ada@acme.test",
    first_name: "Ada",
    last_name: "Lovelace",
    phone_number: "+41 79 000 00 00",
  },
  billing_company_name: "Acme AG",
  billing_street: "Bahnhofstrasse",
  billing_house_number: "1",
  billing_postal_code: "8001",
  billing_city: "Zuerich",
  billing_country: "CH",
  billing_email: "billing@acme.test",
  industries: [{ id: "industry-1", name: "Software" }],
  profile_complete: true,
  missing_profile_fields: [],
};

export const installCompanyProfileHandlers = ({
  company = testCompany,
  profile = testCompanyProfile,
}: {
  company?: MyCompanyResponse;
  profile?: CompanyProfileResponse;
} = {}) => {
  server.use(
    http.get(`${testBackendUrl}/api/company/me`, () =>
      HttpResponse.json(company),
    ),
    http.get(`${testBackendUrl}/api/company/me/profile`, () =>
      HttpResponse.json(profile),
    ),
  );
};

export const testBookletPage: BookletPageResponse = {
  png_base64: "iVBORw0KGgo=",
  overflow: false,
};

export interface BookletPageRequest {
  url: string;
  body: Record<string, unknown>;
}

export const installBookletPageHandler = (
  page: BookletPageResponse = testBookletPage,
  { allowedRequests = Infinity }: { allowedRequests?: number } = {},
) => {
  const requests: BookletPageRequest[] = [];
  server.use(
    http.post(
      `${testBackendUrl}/api/company/:scope/profile/booklet-page`,
      async ({ request }) => {
        requests.push({
          url: request.url,
          body: (await request.json()) as Record<string, unknown>,
        });
        if (requests.length > allowedRequests) {
          return HttpResponse.json(
            { code: "error.rate_limited", message: "Too many requests" },
            { status: 429 },
          );
        }
        return HttpResponse.json(page);
      },
    ),
  );
  return requests;
};

export const profileConfirmCheckbox = () =>
  screen.findByRole(
    "checkbox",
    { name: /kp\.booking\.profile_confirm_checkbox/ },
    SLOW_WAIT,
  );

export const continueToZoneButton = () =>
  screen.getByRole("button", { name: "kp.booking.continue_to_zone" });

export const confirmProfileStep = async (user: UserEvent) => {
  await user.click(await profileConfirmCheckbox());
  await user.click(continueToZoneButton());
  await screen.findByText("kp.booking.select_zone", undefined, SLOW_WAIT);
};
