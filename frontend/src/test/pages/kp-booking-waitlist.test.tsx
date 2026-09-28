import { beforeEach, describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingDetails from "../../pages/KpBookingDetails";
import type { StaffBookingUpgradeWaitlistEntryResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { emptyVenueHandler } from "../fixtures/venue";
import {
  acmeBooking,
  acmeBookingId,
  testMainHallZone,
  testSideHallZone,
} from "../fixtures/staff-bookings";

const detailsPath = "/kp/:id/bookings/:bookingId";
const detailsRoute = `/kp/${testEventId}/bookings/${acmeBookingId}`;

const waitlistEntries: StaffBookingUpgradeWaitlistEntryResponse[] = [
  {
    id: "waitlist-1",
    booking_id: acmeBookingId,
    target_booth_zone_id: testMainHallZone.id,
    target_booth_zone: testMainHallZone,
    priority_rank: 1,
    is_full: false,
    available_spots: 2,
    position: 3,
  },
  {
    id: "waitlist-2",
    booking_id: acmeBookingId,
    target_booth_zone_id: testSideHallZone.id,
    target_booth_zone: testSideHallZone,
    priority_rank: 2,
    is_full: true,
    available_spots: 0,
    position: 1,
  },
];

const renderDetails = () =>
  renderWithProviders(
    <Routes>
      <Route path={detailsPath} element={<KpBookingDetails />} />
    </Routes>,
    { route: detailsRoute },
  );

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    emptyVenueHandler,
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/staff/events/:eventId/bookings/:bookingId/requirement-files`,
      () => HttpResponse.json({ files: {} }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
      HttpResponse.json([acmeBooking]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/booth-zones`, () =>
      HttpResponse.json([testMainHallZone, testSideHallZone]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/services`, () =>
      HttpResponse.json([]),
    ),
  );
});

describe("the booking upgrade waitlist card", () => {
  it("lists every target zone with its position and free spots", async () => {
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
        () => HttpResponse.json({ ...acmeBooking, waitlist_count: 2 }),
      ),
      http.get(
        `${testBackendUrl}/api/kp/staff/bookings/:bookingId/upgrade-waitlist`,
        () => HttpResponse.json(waitlistEntries),
      ),
    );
    renderDetails();

    expect(
      await screen.findByText(
        "kp.manage.booking_waitlist_title",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();

    const waitlistTable = (
      await screen.findByText("kp.manage.booking_waitlist_zone")
    ).closest("table") as HTMLElement;
    const rows = within(waitlistTable)
      .getAllByRole("row")
      .slice(1)
      .map((row) =>
        within(row)
          .getAllByRole("cell")
          .map((cell) => cell.textContent),
      );

    expect(rows).toEqual([
      ["Main hall", "3", "2"],
      ["Side hall", "1", "0"],
    ]);
  });

  it("says nothing is queued when the booking waits for no zone", async () => {
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
        () => HttpResponse.json({ ...acmeBooking, waitlist_count: 0 }),
      ),
    );
    renderDetails();

    expect(
      await screen.findByText(
        "kp.manage.booking_waitlist_empty",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
  });

  it("keeps the rest of the page usable when the waitlist cannot be loaded", async () => {
    server.use(
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
        () => HttpResponse.json({ ...acmeBooking, waitlist_count: 1 }),
      ),
      http.get(
        `${testBackendUrl}/api/kp/staff/bookings/:bookingId/upgrade-waitlist`,
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    renderDetails();

    expect(
      await screen.findByText(
        "kp.manage.booking_waitlist_error",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.manage.booking_edit_title"),
    ).toBeInTheDocument();
  });
});
