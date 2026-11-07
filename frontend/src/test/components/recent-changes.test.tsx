import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import RecentChanges from "../../components/home/RecentChanges";
import BookingsTab from "../../components/kp-manage/BookingsTab";
import {
  KpBookingStatus,
  type RecentChangesResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { staffBookings } from "../fixtures/staff-bookings";

const since = "2026-10-01T10:00:00Z";
const asOf = "2026-10-03T10:00:00Z";

const changes: RecentChangesResponse = {
  since,
  as_of: asOf,
  new_users: [
    {
      id: "user-1",
      email: "neu@example.com",
      first_name: "Nora",
      last_name: "Neu",
      company_name: "Neu AG",
      created_at: "2026-10-02T10:00:00Z",
    },
  ],
  new_users_total: 1,
  new_companies: [
    {
      id: "company-1",
      name: "Neu AG",
      confirmed_at: null,
      created_at: "2026-10-02T10:00:00Z",
    },
  ],
  new_companies_total: 1,
  new_bookings: [
    {
      id: "booking-1",
      event_id: testEventId,
      event_name: "KP 2026",
      company_id: "company-1",
      company_name: "Neu AG",
      booth_zone_name: "Main hall",
      status: KpBookingStatus.REGISTERED,
      created_at: "2026-10-02T10:00:00Z",
      changed_at: "2026-10-02T10:00:00Z",
    },
  ],
  new_bookings_total: 1,
  new_booking_events: [{ id: testEventId, name: "KP 2026" }],
  changed_bookings: [],
  changed_bookings_total: 0,
  changed_booking_events: [],
};

let seenCalls = 0;
let seenBodies: unknown[] = [];

beforeEach(() => {
  seenCalls = 0;
  seenBodies = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/changes`, () =>
      HttpResponse.json(
        seenCalls > 0
          ? { ...changes, new_users: [], new_users_total: 0 }
          : changes,
      ),
    ),
    http.post(`${testBackendUrl}/api/changes/seen`, async ({ request }) => {
      seenCalls += 1;
      seenBodies.push(await request.json());
      return new HttpResponse(null, { status: 204 });
    }),
  );
});

describe("the recent changes section", () => {
  it("lists what is new and links to the filtered pages", async () => {
    renderWithProviders(<RecentChanges />);

    expect(await screen.findByText("Nora Neu")).toBeInTheDocument();
    expect(screen.getAllByText("Neu AG").length).toBeGreaterThan(0);
    const showAll = screen.getAllByRole("link", { name: "changes.show_all" });
    expect(showAll.map((link) => link.getAttribute("href"))).toContain(
      `/kp/${testEventId}?tab=bookings&changes=1`,
    );
    expect(showAll.map((link) => link.getAttribute("href"))).toContain(
      "/user-management?filter=new",
    );
    expect(showAll.map((link) => link.getAttribute("href"))).toContain(
      "/company-management?filter=new",
    );
  });

  it("marks everything as seen", async () => {
    const { user } = renderWithProviders(<RecentChanges />);

    await screen.findByText("Nora Neu");
    await user.click(screen.getByRole("button", { name: "changes.mark_seen" }));

    await waitFor(() => {
      expect(screen.queryByText("Nora Neu")).not.toBeInTheDocument();
    });
    expect(seenCalls).toBe(1);
    expect(seenBodies).toEqual([{ as_of: asOf }]);
  });

  it("links the bookings of each column to their own event", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/changes`, () =>
        HttpResponse.json({
          ...changes,
          changed_bookings: [
            {
              ...changes.new_bookings[0],
              id: "booking-2",
              event_id: "event-b",
              company_name: "Other AG",
            },
          ],
          changed_bookings_total: 1,
          changed_booking_events: [{ id: "event-b", name: "KP B" }],
        }),
      ),
    );
    renderWithProviders(<RecentChanges />);

    await screen.findByText("Other AG");
    const links = screen
      .getAllByRole("link", { name: "changes.show_all" })
      .map((link) => link.getAttribute("href"));
    expect(links).toContain(`/kp/${testEventId}?tab=bookings&changes=1`);
    expect(links).toContain("/kp/event-b?tab=bookings&changes=1");
  });

  it("links every event with changes, not only the listed ones", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/changes`, () =>
        HttpResponse.json({
          ...changes,
          new_booking_events: [
            { id: testEventId, name: "KP 2026" },
            { id: "event-b", name: "KP B" },
          ],
        }),
      ),
    );
    renderWithProviders(<RecentChanges />);

    const links = await screen.findAllByRole("link", {
      name: "changes.show_event",
    });
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      `/kp/${testEventId}?tab=bookings&changes=1`,
      "/kp/event-b?tab=bookings&changes=1",
    ]);
  });

  it("shows an error when the changes cannot be loaded", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/changes`, () =>
        HttpResponse.json({ code: "server.error" }, { status: 500 }),
      ),
    );
    renderWithProviders(<RecentChanges />);

    expect(await screen.findByText("error.load_failed")).toBeInTheDocument();
  });
});

describe("the bookings table change filter", () => {
  it("shows only bookings changed since the last visit", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
        HttpResponse.json(
          staffBookings.map((booking, index) => ({
            ...booking,
            changed_at:
              index === 0 ? "2026-10-05T10:00:00Z" : "2026-09-01T10:00:00Z",
          })),
        ),
      ),
    );
    renderWithProviders(<BookingsTab eventId={testEventId} />, {
      route: "/?changes=1",
    });

    const first = staffBookings[0].company.name;
    await screen.findByText(first, {}, { timeout: 5000 });
    await waitFor(() => {
      expect(
        screen.getAllByRole("link").map((link) => link.textContent),
      ).toEqual([first]);
    });
  });
});
