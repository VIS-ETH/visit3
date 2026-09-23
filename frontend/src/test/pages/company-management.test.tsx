import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse, type DefaultBodyType } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { UserProvider } from "../../context/UserContext";
import type {
  CompanyListResult,
  UserResponse,
} from "../../orval/generated/fastAPI.schemas";
import CompanyManagement from "../../pages/CompanyManagement";
import { testBackendUrl } from "../constants";
import {
  acmeCompany,
  adminUser,
  globexCompany,
  memberUser,
  orphanUser,
  staffUser,
} from "../fixtures/admin";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { server } from "../server";

let listRequests: URL[] = [];
let renameBodies: { companyId: string; body: unknown }[] = [];
let addedMembers: { companyId: string; body: unknown }[] = [];
let removedMembers: { companyId: string; userId: string }[] = [];
let deleteCalls: { companyId: string; variant: string }[] = [];
let companies: CompanyListResult[] = [];
let companyTotal = 2;
let companyMembers: UserResponse[] = [];
let deleteResponse: () => HttpResponse<DefaultBodyType>;

const lastListParams = () => {
  const url = listRequests[listRequests.length - 1];
  return {
    query: url.searchParams.get("query"),
    page: url.searchParams.get("page"),
    pageSize: url.searchParams.get("page_size"),
  };
};

beforeEach(() => {
  listRequests = [];
  renameBodies = [];
  addedMembers = [];
  removedMembers = [];
  deleteCalls = [];
  companies = [acmeCompany, globexCompany];
  companyTotal = 2;
  companyMembers = [memberUser];
  deleteResponse = () => new HttpResponse(null, { status: 204 });
  localStorage.setItem("token", createToken(3600));

  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/companies`, ({ request }) => {
      const url = new URL(request.url);
      listRequests.push(url);
      return HttpResponse.json({
        items: companies,
        total: companyTotal,
        page: Number(url.searchParams.get("page") ?? 1),
        page_size: Number(url.searchParams.get("page_size") ?? 25),
      });
    }),
    http.patch(
      `${testBackendUrl}/api/companies/:companyId`,
      async ({ params, request }) => {
        renameBodies.push({
          companyId: String(params.companyId),
          body: await request.json(),
        });
        return HttpResponse.json({ id: params.companyId, name: "Renamed AG" });
      },
    ),
    http.get(`${testBackendUrl}/api/company/:companyId/users`, () =>
      HttpResponse.json(companyMembers),
    ),
    http.get(`${testBackendUrl}/api/users`, () =>
      HttpResponse.json({
        items: [orphanUser, memberUser],
        total: 2,
        page: 1,
        page_size: 20,
      }),
    ),
    http.post(
      `${testBackendUrl}/api/companies/:companyId/members`,
      async ({ params, request }) => {
        addedMembers.push({
          companyId: String(params.companyId),
          body: await request.json(),
        });
        return HttpResponse.json(orphanUser);
      },
    ),
    http.delete(
      `${testBackendUrl}/api/companies/:companyId/members/:userId`,
      ({ params }) => {
        removedMembers.push({
          companyId: String(params.companyId),
          userId: String(params.userId),
        });
        return new HttpResponse(null, { status: 204 });
      },
    ),
    http.delete(
      `${testBackendUrl}/api/company/:companyId/delete-keep-users`,
      ({ params }) => {
        deleteCalls.push({
          companyId: String(params.companyId),
          variant: "keep-users",
        });
        return deleteResponse();
      },
    ),
    http.delete(
      `${testBackendUrl}/api/company/:companyId/delete-with-users`,
      ({ params }) => {
        deleteCalls.push({
          companyId: String(params.companyId),
          variant: "with-users",
        });
        return deleteResponse();
      },
    ),
  );
});

const renderPage = (currentUser: UserResponse = adminUser) =>
  renderWithProviders(
    <UserProvider user={currentUser} isLoading={false}>
      <CompanyManagement />
    </UserProvider>,
  );

const acmeRow = async () => {
  const cell = await screen.findByText(acmeCompany.name);
  const row = cell.closest("tr");
  if (!row) throw new Error("row not found");
  return within(row);
};

describe("the company management page", () => {
  it("lists companies with members and bookings", async () => {
    renderPage();
    const row = await acmeRow();

    expect(lastListParams()).toEqual({
      query: null,
      page: "1",
      pageSize: "25",
    });
    expect(row.getByText(String(acmeCompany.users_count))).toBeInTheDocument();
    expect(
      row.getByText(String(acmeCompany.bookings_count)),
    ).toBeInTheDocument();
  });

  it("sends the debounced search and resets the page", async () => {
    companyTotal = 60;
    const { user } = renderPage();
    await acmeRow();

    await user.click(screen.getByRole("button", { name: "2" }));
    await waitFor(() => {
      expect(lastListParams().page).toBe("2");
    });

    await user.type(
      screen.getByPlaceholderText("company_management.search_placeholder"),
      "acm",
    );

    await waitFor(() => {
      expect(lastListParams()).toEqual({
        query: "acm",
        page: "1",
        pageSize: "25",
      });
    });
  });

  it("renames a company inline", async () => {
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.rename" }),
    );
    const input = row.getByLabelText("company_management.rename");
    await user.clear(input);
    await user.type(input, "Renamed AG");
    await user.click(
      row.getByRole("button", { name: "company_management.rename_save" }),
    );

    await waitFor(() => {
      expect(renameBodies).toEqual([
        { companyId: acmeCompany.id, body: { name: "Renamed AG" } },
      ]);
    });
  });

  it("removes a member from the members drawer", async () => {
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.view_users" }),
    );
    await screen.findByText(memberUser.email);
    await user.click(
      screen.getByRole("button", { name: "company_management.members.remove" }),
    );

    await waitFor(() => {
      expect(removedMembers).toEqual([
        { companyId: acmeCompany.id, userId: memberUser.id },
      ]);
    });
  });

  it("only offers users without a company when adding a member", async () => {
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.view_users" }),
    );
    const select = await screen.findByPlaceholderText(
      "company_management.members.add_placeholder",
    );
    await user.click(select);

    expect(
      await screen.findByRole("option", { name: new RegExp(orphanUser.email) }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: new RegExp(memberUser.email) }),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("option", { name: new RegExp(orphanUser.email) }),
    );
    await user.click(
      screen.getByRole("button", {
        name: "company_management.members.add_submit",
      }),
    );

    await waitFor(() => {
      expect(addedMembers).toEqual([
        { companyId: acmeCompany.id, body: { user_id: orphanUser.id } },
      ]);
    });
  });

  it("hides the delete action from a non-admin staff user", async () => {
    renderPage(staffUser);
    const row = await acmeRow();

    expect(
      row.queryByRole("button", { name: "company_management.delete" }),
    ).not.toBeInTheDocument();
  });

  it("deletes a company and keeps its users", async () => {
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.delete" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "company_management.delete_modal.keep_users",
      }),
    );

    await waitFor(() => {
      expect(deleteCalls).toEqual([
        { companyId: acmeCompany.id, variant: "keep-users" },
      ]);
    });
  });

  it("deletes a company together with its users", async () => {
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.delete" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "company_management.delete_modal.delete_with_users",
      }),
    );

    await waitFor(() => {
      expect(deleteCalls).toEqual([
        { companyId: acmeCompany.id, variant: "with-users" },
      ]);
    });
  });

  it("shows the conflict text when the company still has bookings", async () => {
    deleteResponse = () =>
      HttpResponse.json(
        {
          statusCode: 409,
          code: "error.company_has_upcoming_bookings",
          identifier: "delete_company",
          message: "upcoming bookings",
        },
        { status: 409 },
      );
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.delete" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "company_management.delete_modal.keep_users",
      }),
    );

    expect(
      await screen.findByText("error.company_has_upcoming_bookings"),
    ).toBeInTheDocument();
  });
});
