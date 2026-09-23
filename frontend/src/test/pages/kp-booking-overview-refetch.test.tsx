import { act } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManageOverview from "../../pages/KpBookingManageOverview";
import { getGetMyBookingQueryKey } from "../../orval/generated/kp/kp";
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

const overviewPath = "/kp/:id/booking/:bookingId/manage";
const overviewRoute = `/kp/${testEventId}/booking/${testBookingId}/manage`;

const openEvent = {
  ...testEvent,
  finalization_deadline: "2099-12-31",
  registration_open: "2000-01-01",
  registration_end: "2099-12-31",
  event_date: "2099-12-31",
};

let bookingRequests = 0;
let releasePendingBooking: () => void;
let pendingBooking: Promise<void>;

beforeEach(() => {
  bookingRequests = 0;
  pendingBooking = new Promise<void>((resolve) => {
    releasePendingBooking = resolve;
  });
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(openEvent),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/my-booking`,
      async () => {
        bookingRequests += 1;
        if (bookingRequests > 1) await pendingBooking;
        return HttpResponse.json(testBooking);
      },
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/booth-zones/available`,
      () =>
        HttpResponse.json([
          {
            ...testMainZone,
            id: testBooking.booth_zone_id,
            available_spots: 2,
          },
          { ...testMainZone, available_spots: 3 },
        ]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/bookings/:bookingId/upgrade-waitlist`,
      () => HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/bookings/:bookingId/nametags`, () =>
      HttpResponse.json([]),
    ),
    emptyVenueHandler,
  );
});

describe("the booking overview background refetch", () => {
  it("keeps the open zone switch mounted while the booking refetches", async () => {
    const { user, queryClient } = renderWithProviders(
      <Routes>
        <Route path={overviewPath} element={<KpBookingManageOverview />} />
      </Routes>,
      { route: overviewRoute },
    );

    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.zone_switch.open" },
        { timeout: 5000 },
      ),
    );
    await screen.findByRole("group", { name: "kp.zone_switch.zone_list" });

    await act(async () => {
      void queryClient.invalidateQueries({
        queryKey: getGetMyBookingQueryKey(testEventId),
      });
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(bookingRequests).toBe(2);
    });
    expect(
      screen.getByRole("group", { name: "kp.zone_switch.zone_list" }),
    ).toBeInTheDocument();

    releasePendingBooking();

    await waitFor(() => {
      expect(
        screen.getByRole("group", { name: "kp.zone_switch.zone_list" }),
      ).toBeInTheDocument();
    });
  });
});
