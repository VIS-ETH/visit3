import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManageOverview from "../../pages/KpBookingManageOverview";
import KpCompanyView from "../../pages/KpCompanyView";
import {
  KpBookingStatus,
  type BookingResponse,
  type BoothZoneWithAvailabilityResponse,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEvent,
  testEventId,
} from "../fixtures/kp-booking";
import { emptyVenueHandler, testMainZone } from "../fixtures/venue";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const openEvent: KpResponse = {
  ...testEvent,
  finalization_deadline: "2099-12-31",
  registration_open: "2000-01-01",
  registration_end: "2099-12-31",
  event_date: "2099-12-31",
};

const closedEvent: KpResponse = {
  ...openEvent,
  finalization_deadline: "2000-01-01",
};

const currentZone: BoothZoneWithAvailabilityResponse = {
  id: testBooking.booth_zone_id,
  event_id: testEventId,
  name: "Main hall",
  description: "Main hall zone",
  color: "#112233",
  order: 1,
  capacity: 20,
  booth_size: 6,
  base_price: 50000,
  included_services: [],
  available_spots: 2,
};

const freeZone: BoothZoneWithAvailabilityResponse = {
  ...testMainZone,
  available_spots: 3,
  base_price: 60000,
};

const overviewPath = "/kp/:id/booking/:bookingId/manage";
const overviewRoute = `/kp/${testEventId}/booking/${testBookingId}/manage`;

let event: KpResponse = openEvent;
let booking: BookingResponse = testBooking;
let bookingRequests = 0;

const renderOverview = () =>
  renderWithProviders(
    <Routes>
      <Route path={overviewPath} element={<KpBookingManageOverview />} />
    </Routes>,
    { route: overviewRoute },
  );

const renderCompanyView = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp/:id" element={<KpCompanyView />} />
    </Routes>,
    { route: `/kp/${testEventId}` },
  );

beforeEach(() => {
  event = openEvent;
  booking = testBooking;
  bookingRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(event),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () => {
      bookingRequests += 1;
      return HttpResponse.json(booking);
    }),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/booth-zones/available`,
      () => HttpResponse.json([currentZone, freeZone]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/bookings/:bookingId/upgrade-waitlist`,
      () => HttpResponse.json([]),
    ),
    emptyVenueHandler,
  );
});

describe("the booking overview zone options", () => {
  it("shows the zone switch and the waitlist card", async () => {
    renderOverview();

    expect(
      await screen.findByText("kp.zone_switch.title", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(screen.getByText("kp.waitlist.title")).toBeInTheDocument();
    expect(
      await screen.findByText("kp.waitlist.empty", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
  });

  it("reloads the booking after a zone switch", async () => {
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/${testBookingId}/switch-zone`,
        () => {
          booking = { ...testBooking, booth_zone_id: freeZone.id };
          return HttpResponse.json(booking);
        },
      ),
    );
    const { user } = renderOverview();

    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.zone_switch.open" },
        SLOW_WAIT,
      ),
    );
    const list = await screen.findByRole(
      "group",
      {
        name: "kp.zone_switch.zone_list",
      },
      SLOW_WAIT,
    );
    await user.click(
      within(list).getByRole("button", { name: new RegExp(freeZone.name) }),
    );
    await user.click(
      screen.getByRole("button", { name: "kp.zone_switch.switch_action" }),
    );
    await user.click(
      screen.getByRole("button", { name: "kp.zone_switch.confirm_submit" }),
    );

    await waitFor(() => {
      expect(bookingRequests).toBeGreaterThan(1);
    }, SLOW_WAIT);
  });
});

describe("the company event view", () => {
  it("hints that the booth zone can still be changed", async () => {
    renderCompanyView();

    expect(
      await screen.findByText(
        "kp.zone_switch.company_hint",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
  });

  it("drops the hint once the booking can no longer switch", async () => {
    event = closedEvent;
    booking = { ...testBooking, status: KpBookingStatus.FINALIZED };
    renderCompanyView();

    await screen.findByText(
      "kp.company_view.manage_booking",
      undefined,
      SLOW_WAIT,
    );
    expect(
      screen.queryByText("kp.zone_switch.company_hint"),
    ).not.toBeInTheDocument();
  });
});
