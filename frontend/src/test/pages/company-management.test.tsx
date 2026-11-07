import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse, type DefaultBodyType } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Route, Routes, useLocation, useParams } from "react-router";
import { UserProvider } from "../../context/UserContext";
import {
  KpBookingStatus,
  type CompanyListResult,
  type KpResponse,
  type StaffBookingResponse,
  type StaffUserResponse,
  type UserResponse,
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
import { testOpenEvent, testStaffBooking } from "../fixtures/kp-booking";
import { renderWithProviders } from "../render";
import { reloadAt } from "../../utils/navigation";

vi.mock("../../utils/navigation", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../utils/navigation")>()),
  reloadAt: vi.fn(),
}));
import { server } from "../server";
import { notificationsShow } from "../notifications";

let listRequests: URL[] = [];
let renameBodies: { companyId: string; body: unknown }[] = [];
let addedMembers: { companyId: string; body: unknown }[] = [];
let removedMembers: { companyId: string; userId: string }[] = [];
let deleteCalls: { companyId: string; variant: string }[] = [];
let companies: CompanyListResult[] = [];
let companyTotal = 2;
let companyMembers: StaffUserResponse[] = [];
let deleteResponse: () => HttpResponse<DefaultBodyType>;
let latestEvent: KpResponse | null = null;
const olderEvent: KpResponse = {
  ...testOpenEvent,
  id: "event-older",
  name: "Kontaktparty 2000",
  event_date: "2000-01-02",
};
let eventBookings: StaffBookingResponse[] = [];
let bookingActions: string[] = [];

const BookingRouteProbe = () => {
  const { id, bookingId } = useParams();
  return <p>{`${id}/${bookingId}`}</p>;
};

const LocationProbe = () => {
  const location = useLocation();
  return <p>{`${location.pathname}${location.search}`}</p>;
};

const acmeBooking = (status: KpBookingStatus): StaffBookingResponse => ({
  ...testStaffBooking,
  company_id: acmeCompany.id,
  company: { id: acmeCompany.id, name: acmeCompany.name },
  status,
});

const setAcmeStatus = (status: KpBookingStatus) => {
  eventBookings = [acmeBooking(status)];
  return HttpResponse.json(eventBookings[0]);
};

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
  latestEvent = null;
  eventBookings = [];
  bookingActions = [];
  localStorage.setItem("token", createToken(3600));

  server.use(
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
    http.get(`${testBackendUrl}/api/kp/list`, () =>
      HttpResponse.json(latestEvent ? [latestEvent, olderEvent] : [olderEvent]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
      HttpResponse.json(eventBookings),
    ),
    http.post(`${testBackendUrl}/api/kp/bookings/:bookingId/accept`, () => {
      bookingActions.push("accept");
      return setAcmeStatus(KpBookingStatus.CONFIRMED);
    }),
    http.post(
      `${testBackendUrl}/api/kp/bookings/:bookingId/undo-accept`,
      () => {
        bookingActions.push("undo-accept");
        return setAcmeStatus(KpBookingStatus.REGISTERED);
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

  it("sorts by member count on the server", async () => {
    const { user } = renderPage();
    await screen.findByText(acmeCompany.name);

    await user.click(
      screen.getByRole("button", { name: "company_management.users_count" }),
    );
    await user.click(
      screen.getByRole("button", { name: "company_management.users_count" }),
    );

    await waitFor(() => {
      expect(
        listRequests[listRequests.length - 1].searchParams.get("direction"),
      ).toBe("desc");
    });
    expect(listRequests[listRequests.length - 1].searchParams.get("sort")).toBe(
      "members",
    );
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

  it("impersonates a member and remembers where it started", async () => {
    const { user } = renderWithProviders(
      <UserProvider user={adminUser} isLoading={false}>
        <CompanyManagement />
      </UserProvider>,
      { route: "/company-management" },
    );
    const row = await acmeRow();
    await user.click(
      row.getByRole("button", { name: "company_management.view_users" }),
    );
    await screen.findByText(memberUser.email);

    await user.click(
      screen.getByRole("button", { name: "user_management.impersonate" }),
    );

    expect(reloadAt).toHaveBeenCalledWith("/");
    expect(sessionStorage.getItem("impersonating_user_id")).toBe(memberUser.id);
    expect(sessionStorage.getItem("impersonation_origin")).toBe(
      "/company-management",
    );
  });

  it("edits a member and links to the user management", async () => {
    const { user } = renderPage(staffUser);
    const row = await acmeRow();
    await user.click(
      row.getByRole("button", { name: "company_management.view_users" }),
    );
    await screen.findByText(memberUser.email);

    expect(
      screen.queryByRole("button", { name: "user_management.impersonate" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "company_management.members.open_in_user_management",
      }),
    ).toHaveAttribute(
      "href",
      `/user-management?query=${encodeURIComponent(acmeCompany.name).replaceAll("%20", "+")}`,
    );

    await user.click(
      screen.getByRole("button", { name: "user_management.edit.title" }),
    );

    expect(
      await screen.findByDisplayValue(memberUser.email),
    ).toBeInTheDocument();
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

describe("confirming bookings from the company management", () => {
  const globexRow = async () => {
    const cell = await screen.findByText(globexCompany.name);
    const row = cell.closest("tr");
    if (!row) throw new Error("row not found");
    return within(row);
  };

  it("confirms the pending booking of the upcoming event", async () => {
    latestEvent = testOpenEvent;
    eventBookings = [acmeBooking(KpBookingStatus.REGISTERED)];
    const { user } = renderPage(staffUser);
    const row = await acmeRow();

    expect(
      await row.findByText("kp.booking.status.registered.label"),
    ).toBeInTheDocument();
    await user.click(
      row.getByRole("button", { name: "kp.manage.booking_action_accept" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "kp.manage.booking_accept_submit",
      }),
    );

    expect(
      await row.findByText("kp.booking.status.confirmed.label"),
    ).toBeInTheDocument();
    expect(bookingActions).toEqual(["accept"]);
    expect(
      row.getByRole("button", { name: "kp.manage.booking_action_undo_accept" }),
    ).toBeInTheDocument();
  });

  it("opens the booking next to its confirm action", async () => {
    latestEvent = testOpenEvent;
    eventBookings = [acmeBooking(KpBookingStatus.REGISTERED)];
    const { user } = renderWithProviders(
      <UserProvider user={staffUser} isLoading={false}>
        <Routes>
          <Route path="/" element={<CompanyManagement />} />
          <Route
            path="/kp/:id/bookings/:bookingId"
            element={<BookingRouteProbe />}
          />
        </Routes>
      </UserProvider>,
    );
    const row = await acmeRow();

    await user.click(
      await row.findByRole("link", { name: "company_management.view_booking" }),
    );

    expect(
      await screen.findByText(`${testOpenEvent.id}/${testStaffBooking.id}`),
    ).toBeInTheDocument();
  });

  it("undoes a confirmation like the booking page", async () => {
    latestEvent = testOpenEvent;
    eventBookings = [acmeBooking(KpBookingStatus.CONFIRMED)];
    const { user } = renderPage(staffUser);
    const row = await acmeRow();

    await user.click(
      await row.findByRole("button", {
        name: "kp.manage.booking_action_undo_accept",
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "kp.manage.booking_undo_accept_submit",
      }),
    );

    expect(
      await row.findByText("kp.booking.status.registered.label"),
    ).toBeInTheDocument();
    expect(bookingActions).toEqual(["undo-accept"]);
  });

  it("flags a confirmed booking with new additions", async () => {
    latestEvent = testOpenEvent;
    eventBookings = [
      {
        ...acmeBooking(KpBookingStatus.CONFIRMED),
        added_after_confirmation: [
          {
            booking_service_id: (testStaffBooking.services ?? [])[0].id,
            quantity: 1,
          },
        ],
      },
    ];
    renderPage(staffUser);
    const row = await acmeRow();

    expect(
      await row.findByText("kp.manage.booking_new_additions"),
    ).toBeInTheDocument();
  });

  it("shows no action for a company without a booking", async () => {
    latestEvent = testOpenEvent;
    eventBookings = [acmeBooking(KpBookingStatus.REGISTERED)];
    renderPage(staffUser);
    await (await acmeRow()).findByText("kp.booking.status.registered.label");
    const row = await globexRow();

    expect(
      row.queryByRole("button", { name: "kp.manage.booking_action_accept" }),
    ).not.toBeInTheDocument();
    expect(
      row.queryByText("kp.booking.status.registered.label"),
    ).not.toBeInTheDocument();
  });

  it("shows the bookings of another picked Kontaktparty", async () => {
    latestEvent = testOpenEvent;
    eventBookings = [];
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/bookings`,
        ({ params }) =>
          HttpResponse.json(
            params.eventId === olderEvent.id
              ? [acmeBooking(KpBookingStatus.CONFIRMED)]
              : [],
          ),
      ),
    );
    const { user } = renderPage(staffUser);
    const row = await acmeRow();

    await user.click(
      await screen.findByRole("combobox", {
        name: "kp.bookings_overview.event",
      }),
    );
    await user.click(
      await screen.findByRole("option", { name: olderEvent.name }),
    );

    expect(
      await row.findByText("kp.booking.status.confirmed.label"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: olderEvent.name }),
    ).toBeInTheDocument();
  });

  it("ignores bookings of an event that is already over", async () => {
    latestEvent = { ...testOpenEvent, event_date: "2000-01-02" };
    eventBookings = [acmeBooking(KpBookingStatus.REGISTERED)];
    renderPage(staffUser);
    const row = await acmeRow();

    await waitFor(() => expect(listRequests.length).toBeGreaterThan(0));
    expect(
      row.queryByRole("button", { name: "kp.manage.booking_action_accept" }),
    ).not.toBeInTheDocument();
  });
});

describe("mailing a company", () => {
  it("opens a new mail for the company and the shown event", async () => {
    latestEvent = testOpenEvent;
    const { user } = renderWithProviders(
      <UserProvider
        user={{ ...staffUser, is_kp_president: true }}
        isLoading={false}
      >
        <Routes>
          <Route path="/" element={<CompanyManagement />} />
          <Route path="/admin/mail-campaigns" element={<LocationProbe />} />
        </Routes>
      </UserProvider>,
    );
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.send_mail" }),
    );

    expect(
      await screen.findByText(
        `/admin/mail-campaigns?company=${acmeCompany.id}&event=${testOpenEvent.id}`,
      ),
    ).toBeInTheDocument();
  });

  it("hides the mail action from staff without the organiser role", async () => {
    renderPage(staffUser);
    const row = await acmeRow();

    expect(
      row.queryByRole("button", { name: "company_management.send_mail" }),
    ).not.toBeInTheDocument();
  });
});

describe("company confirmation", () => {
  it("confirms a company the organisers have not approved yet", async () => {
    const confirmed: { companyId: string; body: unknown }[] = [];
    companies = [{ ...acmeCompany, confirmed_at: null }, globexCompany];
    server.use(
      http.post(
        `${testBackendUrl}/api/companies/:companyId/confirm`,
        async ({ params, request }) => {
          confirmed.push({
            companyId: String(params.companyId),
            body: await request.json(),
          });
          return HttpResponse.json({
            id: acmeCompany.id,
            name: acmeCompany.name,
            confirmed_at: "2026-10-20T10:00:00Z",
          });
        },
      ),
    );
    const { user } = renderPage();
    const row = await acmeRow();

    expect(row.getByText("company_management.unconfirmed")).toBeInTheDocument();
    await user.click(
      row.getByRole("button", { name: "company_management.confirm" }),
    );

    await waitFor(() => {
      expect(confirmed).toEqual([
        { companyId: acmeCompany.id, body: { name: acmeCompany.name } },
      ]);
    });
  });

  it("reloads the list when the company was renamed before confirming", async () => {
    companies = [{ ...acmeCompany, confirmed_at: null }, globexCompany];
    server.use(
      http.post(`${testBackendUrl}/api/companies/:companyId/confirm`, () => {
        companies = [
          { ...acmeCompany, name: "Acme Renamed", confirmed_at: null },
          globexCompany,
        ];
        return HttpResponse.json(
          { statusCode: 409, code: "error.conflict", message: "conflict" },
          { status: 409 },
        );
      }),
    );
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.confirm" }),
    );

    expect(await screen.findByText("Acme Renamed")).toBeInTheDocument();
    expect(notificationsShow).toHaveBeenCalledTimes(1);
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({
        color: "red",
        message: "company_management.confirm_conflict",
      }),
    );
  });

  it("offers no confirmation for an approved company", async () => {
    renderPage();
    const row = await acmeRow();

    expect(
      row.queryByRole("button", { name: "company_management.confirm" }),
    ).not.toBeInTheDocument();
  });
});

describe("new company members", () => {
  it("flags the company row that has new members", async () => {
    companies = [{ ...acmeCompany, new_members_count: 1 }, globexCompany];
    renderPage();
    const row = await acmeRow();

    expect(
      row.getByText("kp.manage.booking_new_additions"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("kp.manage.booking_new_additions")).toHaveLength(
      1,
    );
  });

  it("marks the new members as seen from the members drawer", async () => {
    const acknowledged: string[] = [];
    companyMembers = [
      { ...memberUser, new_in_company_since: "2026-09-26T10:00:00Z" },
    ];
    server.use(
      http.post(
        `${testBackendUrl}/api/companies/:companyId/members/acknowledge`,
        ({ params }) => {
          acknowledged.push(String(params.companyId));
          companyMembers = [{ ...memberUser, new_in_company_since: null }];
          return HttpResponse.json(companyMembers);
        },
      ),
    );
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.view_users" }),
    );
    const drawer = await screen.findByRole("dialog");
    expect(
      await within(drawer).findByText("kp.manage.booking_new_additions"),
    ).toBeInTheDocument();
    await user.click(
      within(drawer).getByRole("button", {
        name: "company_management.members.acknowledge",
      }),
    );

    await waitFor(() => expect(acknowledged).toEqual([acmeCompany.id]));
    await waitFor(() =>
      expect(
        within(drawer).queryByText("kp.manage.booking_new_additions"),
      ).not.toBeInTheDocument(),
    );
    expect(
      within(drawer).queryByRole("button", {
        name: "company_management.members.acknowledge",
      }),
    ).not.toBeInTheDocument();
  });
});

describe("company list paging", () => {
  const pagedCompany = (i: number): CompanyListResult => ({
    id: `00000000-0000-0000-0000-${String(i).padStart(12, "0")}`,
    name: `Company ${String(i).padStart(2, "0")}`,
    confirmed_at: "2026-01-01T00:00:00Z",
    users_count: 0,
    bookings_count: 0,
  });

  beforeEach(() => {
    companies = Array.from({ length: 26 }, (_, i) => pagedCompany(i + 1));
    server.use(
      http.get(`${testBackendUrl}/api/companies`, ({ request }) => {
        const url = new URL(request.url);
        listRequests.push(url);
        const page = Number(url.searchParams.get("page") ?? 1);
        const size = Number(url.searchParams.get("page_size") ?? 25);
        return HttpResponse.json({
          items: companies.slice((page - 1) * size, page * size),
          total: companies.length,
          page,
          page_size: size,
        });
      }),
      http.delete(
        `${testBackendUrl}/api/company/:companyId/delete-keep-users`,
        ({ params }) => {
          companies = companies.filter((c) => c.id !== params.companyId);
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );
  });

  const rowOf = async (name: string) => {
    const cell = await screen.findByText(name);
    return within(cell.closest("tr")!);
  };

  it("goes back a page after deleting the only company on the last page", async () => {
    const { user } = renderPage();
    await screen.findByText("Company 01");
    await user.click(screen.getByRole("button", { name: "2" }));
    const row = await rowOf("Company 26");

    await user.click(
      row.getByRole("button", { name: "company_management.delete" }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "company_management.delete_modal.keep_users",
      }),
    );

    expect(await screen.findByText("Company 01")).toBeInTheDocument();
    expect(screen.queryByText("Company 26")).not.toBeInTheDocument();
    expect(
      screen.queryByText("company_management.no_companies_description"),
    ).not.toBeInTheDocument();
  });

  it("requests a new search on the first page right away", async () => {
    const { user } = renderPage();
    await screen.findByText("Company 01");
    await user.click(screen.getByRole("button", { name: "2" }));
    await screen.findByText("Company 26");

    await user.type(
      screen.getByPlaceholderText("company_management.search_placeholder"),
      "Company 0",
    );

    await waitFor(() => expect(lastListParams().query).toBe("Company 0"));
    const searchPages = listRequests
      .filter((url) => url.searchParams.get("query") === "Company 0")
      .map((url) => url.searchParams.get("page"));
    expect(searchPages).toEqual(["1"]);
  });
});

describe("inline rename keys", () => {
  it("saves with Enter", async () => {
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.rename" }),
    );
    const input = row.getByLabelText("company_management.rename");
    await user.clear(input);
    await user.type(input, "Renamed AG{Enter}");

    await waitFor(() => {
      expect(renameBodies).toEqual([
        { companyId: acmeCompany.id, body: { name: "Renamed AG" } },
      ]);
    });
  });

  it("cancels with Escape", async () => {
    const { user } = renderPage();
    const row = await acmeRow();

    await user.click(
      row.getByRole("button", { name: "company_management.rename" }),
    );
    await user.type(
      row.getByLabelText("company_management.rename"),
      "X{Escape}",
    );

    expect(row.queryByRole("textbox")).not.toBeInTheDocument();
    expect(renameBodies).toEqual([]);
  });
});

describe("company list filters", () => {
  const renderAt = (route: string) =>
    renderWithProviders(
      <UserProvider user={adminUser} isLoading={false}>
        <CompanyManagement />
        <LocationProbe />
      </UserProvider>,
      { route },
    );

  const lastParam = (name: string) =>
    listRequests[listRequests.length - 1].searchParams.get(name);

  it("lists all companies by default", async () => {
    renderAt("/");
    await acmeRow();

    expect(lastParam("filter")).toBe("all");
    expect(lastParam("company")).toBeNull();
    expect(
      screen.getByRole("radio", { name: "company_management.filters.all" }),
    ).toBeChecked();
  });

  it("filters unconfirmed companies on the first page", async () => {
    companyTotal = 60;
    const { user } = renderAt("/");
    await acmeRow();
    await user.click(screen.getByRole("button", { name: "2" }));
    await waitFor(() => {
      expect(lastParam("page")).toBe("2");
    });

    await user.click(
      screen.getByRole("radio", {
        name: "company_management.filters.unconfirmed",
      }),
    );

    await waitFor(() => {
      expect(lastParam("filter")).toBe("unconfirmed");
    });
    expect(lastParam("page")).toBe("1");
    expect(screen.getByText("/?filter=unconfirmed")).toBeInTheDocument();
  });

  it("opens with the companies new since the last visit", async () => {
    const { user } = renderAt("/?filter=new");
    await acmeRow();

    expect(lastParam("filter")).toBe("new");
    expect(
      screen.getByRole("radio", { name: "company_management.filters.new" }),
    ).toBeChecked();

    await user.click(
      screen.getByRole("radio", { name: "company_management.filters.all" }),
    );

    await waitFor(() => {
      expect(lastParam("filter")).toBe("all");
    });
    expect(screen.getByText("/")).toBeInTheDocument();
  });

  it("shows a single linked company until the filter is cleared", async () => {
    companies = [acmeCompany];
    const { user } = renderAt(`/?company=${acmeCompany.id}`);
    await acmeRow();

    expect(lastParam("company")).toBe(acmeCompany.id);
    expect(
      screen.getByText("company_management.company_filter"),
    ).toBeInTheDocument();

    companies = [acmeCompany, globexCompany];
    await user.click(
      screen.getByRole("button", {
        name: "company_management.clear_company_filter",
      }),
    );

    await waitFor(() => {
      expect(lastParam("company")).toBeNull();
    });
    expect(
      screen.queryByText("company_management.company_filter"),
    ).not.toBeInTheDocument();
    expect(await screen.findByText(globexCompany.name)).toBeInTheDocument();
  });
});
