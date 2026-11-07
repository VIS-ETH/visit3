import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import CompanyMembersDrawer from "../../components/admin/CompanyMembersDrawer";
import type { StaffUserResponse } from "../../orval/generated/fastAPI.schemas";
import { testBackendUrl } from "../constants";
import { acmeCompany, adminUser, memberUser } from "../fixtures/admin";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { server } from "../server";

const userNumber = (
  i: number,
  companyId: string | null,
): StaffUserResponse => ({
  ...memberUser,
  id: `00000000-0000-0000-0000-${String(i).padStart(12, "0")}`,
  email: `u${i}@x.ch`,
  first_name: `U${i}`,
  company_id: companyId,
  company: companyId ? { id: companyId, name: "Other AG" } : null,
});

let users: StaffUserResponse[] = [];

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/users`, ({ request }) => {
      const url = new URL(request.url);
      const page = Number(url.searchParams.get("page") ?? 1);
      const size = Number(url.searchParams.get("page_size") ?? 25);
      return HttpResponse.json({
        items: users.slice((page - 1) * size, page * size),
        total: users.length,
        page,
        page_size: size,
      });
    }),
    http.get(`${testBackendUrl}/api/company/:companyId/users`, () =>
      HttpResponse.json([]),
    ),
  );
});

describe("adding a company member", () => {
  it("offers users without a company that are not on the first result page", async () => {
    users = [
      ...Array.from({ length: 120 }, (_, i) => userNumber(i + 1, "other")),
      userNumber(999, null),
    ];
    const { user } = renderWithProviders(
      <CompanyMembersDrawer
        company={{ id: acmeCompany.id, name: acmeCompany.name }}
        onClose={() => {}}
      />,
      { currentUser: adminUser },
    );

    await screen.findByText("company_management.members.empty");
    await user.click(
      screen.getByPlaceholderText("company_management.members.add_placeholder"),
    );

    expect(
      await screen.findByRole("option", { name: /u999@x\.ch/ }),
    ).toBeInTheDocument();
  });
});
