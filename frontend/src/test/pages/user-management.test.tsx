import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse, type DefaultBodyType } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { UserProvider } from "../../context/UserContext";
import type {
  StaffUserResponse,
  UserResponse,
} from "../../orval/generated/fastAPI.schemas";
import UserManagement from "../../pages/UserManagement";
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
let patchBodies: unknown[] = [];
let confirmedIds: string[] = [];
let resendIds: string[] = [];
let deletedIds: string[] = [];
let listItems: StaffUserResponse[] = [];
let listTotal = 2;
let deleteResponse: () => HttpResponse<DefaultBodyType>;

const lastListRequest = () => listRequests[listRequests.length - 1];

const lastListParams = () => {
  const url = lastListRequest();
  return {
    query: url.searchParams.get("query"),
    filter: url.searchParams.get("filter"),
    page: url.searchParams.get("page"),
    pageSize: url.searchParams.get("page_size"),
  };
};

beforeEach(() => {
  listRequests = [];
  patchBodies = [];
  confirmedIds = [];
  resendIds = [];
  deletedIds = [];
  listItems = [memberUser, orphanUser];
  listTotal = 2;
  deleteResponse = () => new HttpResponse(null, { status: 204 });
  localStorage.setItem("token", createToken(3600));

  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/users`, ({ request }) => {
      const url = new URL(request.url);
      listRequests.push(url);
      return HttpResponse.json({
        items: listItems,
        total: listTotal,
        page: Number(url.searchParams.get("page") ?? 1),
        page_size: Number(url.searchParams.get("page_size") ?? 25),
      });
    }),
    http.get(`${testBackendUrl}/api/companies`, () =>
      HttpResponse.json({
        items: [acmeCompany, globexCompany],
        total: 2,
        page: 1,
        page_size: 20,
      }),
    ),
    http.patch(`${testBackendUrl}/api/users/:userId`, async ({ request }) => {
      patchBodies.push(await request.json());
      return HttpResponse.json(memberUser);
    }),
    http.post(`${testBackendUrl}/api/users/:userId/confirm`, ({ params }) => {
      confirmedIds.push(String(params.userId));
      return HttpResponse.json(memberUser);
    }),
    http.post(
      `${testBackendUrl}/api/users/:userId/resend-confirmation`,
      ({ params }) => {
        resendIds.push(String(params.userId));
        return new HttpResponse(null, { status: 204 });
      },
    ),
    http.delete(`${testBackendUrl}/api/users/:userId`, ({ params }) => {
      deletedIds.push(String(params.userId));
      return deleteResponse();
    }),
  );
});

const renderPage = (currentUser: UserResponse = adminUser) =>
  renderWithProviders(
    <UserProvider user={currentUser} isLoading={false}>
      <UserManagement />
    </UserProvider>,
  );

const memberRow = async () => {
  const cell = await screen.findByText(memberUser.email);
  const row = cell.closest("tr");
  if (!row) throw new Error("row not found");
  return within(row);
};

describe("the user management page", () => {
  it("loads the first page with the default filter", async () => {
    renderPage();

    await waitFor(() => {
      expect(lastListRequest()).toBeDefined();
    });
    expect(lastListParams()).toEqual({
      query: null,
      filter: "all",
      page: "1",
      pageSize: "25",
    });
    expect(await screen.findByText(memberUser.email)).toBeInTheDocument();
  });

  it("sends the debounced search term as a query parameter", async () => {
    const { user } = renderPage();
    await screen.findByText(memberUser.email);

    await user.type(
      screen.getByPlaceholderText("user_management.search_placeholder"),
      "mem",
    );

    await waitFor(() => {
      expect(lastListParams().query).toBe("mem");
    });
    expect(
      listRequests
        .map((url) => url.searchParams.get("query"))
        .filter((query) => query !== null),
    ).toEqual(["mem"]);
  });

  it("sends the selected filter and resets to the first page", async () => {
    listTotal = 60;
    const { user } = renderPage();
    await screen.findByText(memberUser.email);

    await user.click(screen.getByRole("button", { name: "3" }));
    await waitFor(() => {
      expect(lastListParams().page).toBe("3");
    });

    await user.click(
      screen.getByRole("radio", { name: "user_management.filters.staff" }),
    );

    await waitFor(() => {
      expect(lastListParams()).toEqual({
        query: null,
        filter: "staff",
        page: "1",
        pageSize: "25",
      });
    });
  });

  it("confirms a user", async () => {
    const { user } = renderPage();
    const row = await memberRow();

    await user.click(
      row.getByRole("button", { name: "user_management.confirm" }),
    );

    await waitFor(() => {
      expect(confirmedIds).toEqual([memberUser.id]);
    });
  });

  it("resends the confirmation mail", async () => {
    const { user } = renderPage();
    const row = await memberRow();

    await user.click(
      row.getByRole("button", { name: "user_management.resend" }),
    );

    await waitFor(() => {
      expect(resendIds).toEqual([memberUser.id]);
    });
  });

  it("hides the confirm and resend actions for a confirmed user", async () => {
    renderPage();
    const cell = await screen.findByText(orphanUser.email);
    const row = within(cell.closest("tr") as HTMLElement);

    expect(
      row.queryByRole("button", { name: "user_management.confirm" }),
    ).not.toBeInTheDocument();
    expect(
      row.queryByRole("button", { name: "user_management.resend" }),
    ).not.toBeInTheDocument();
  });

  it("saves the edited user including the privilege switches for an admin", async () => {
    const { user } = renderPage();
    const row = await memberRow();

    await user.click(
      row.getByRole("button", { name: "user_management.edit.title" }),
    );
    const firstName = await screen.findByLabelText(
      "user_management.edit.first_name",
    );
    await user.clear(firstName);
    await user.type(firstName, "Memo");
    await user.click(screen.getByLabelText("user_management.edit.is_staff"));
    await user.click(
      screen.getByRole("button", { name: "user_management.edit.save" }),
    );

    await waitFor(() => {
      expect(patchBodies).toHaveLength(1);
    });
    expect(patchBodies[0]).toEqual({
      first_name: "Memo",
      last_name: memberUser.last_name,
      phone_number: memberUser.phone_number,
      email: memberUser.email,
      company_id: memberUser.company_id,
      user_confirmed: false,
      is_staff: true,
      is_admin: false,
    });
  });

  it("hides the privilege switches and omits them for a non-admin staff user", async () => {
    const { user } = renderPage(staffUser);
    const row = await memberRow();

    await user.click(
      row.getByRole("button", { name: "user_management.edit.title" }),
    );
    await screen.findByLabelText("user_management.edit.first_name");

    expect(
      screen.queryByLabelText("user_management.edit.is_staff"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("user_management.edit.is_admin"),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "user_management.edit.save" }),
    );

    await waitFor(() => {
      expect(patchBodies).toHaveLength(1);
    });
    expect(patchBodies[0]).not.toHaveProperty("is_staff");
    expect(patchBodies[0]).not.toHaveProperty("is_admin");
  });

  it("hides the impersonate action from a non-admin staff user", async () => {
    renderPage(staffUser);
    const row = await memberRow();

    expect(
      row.queryByRole("button", { name: "user_management.impersonate" }),
    ).not.toBeInTheDocument();
  });

  it("deletes a user", async () => {
    const { user } = renderPage();
    const row = await memberRow();

    await user.click(
      row.getByRole("button", { name: "user_management.delete" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "user_management.delete_modal.confirm",
      }),
    );

    await waitFor(() => {
      expect(deletedIds).toEqual([memberUser.id]);
    });
  });

  it("shows the conflict text when the user is the last company member", async () => {
    deleteResponse = () =>
      HttpResponse.json(
        {
          statusCode: 409,
          code: "error.user_last_company_member",
          identifier: "delete_user",
          message: "last member",
        },
        { status: 409 },
      );
    const { user } = renderPage();
    const row = await memberRow();

    await user.click(
      row.getByRole("button", { name: "user_management.delete" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "user_management.delete_modal.confirm",
      }),
    );

    expect(
      await screen.findByText("error.user_last_company_member"),
    ).toBeInTheDocument();
  });
});

describe("new company members in the user management", () => {
  it("flags a user who recently joined a company", async () => {
    listItems = [
      { ...memberUser, new_in_company_since: "2026-09-26T10:00:00Z" },
      orphanUser,
    ];
    renderPage();

    const row = await memberRow();

    expect(
      row.getByText("kp.manage.booking_new_additions"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("kp.manage.booking_new_additions")).toHaveLength(
      1,
    );
  });
});
