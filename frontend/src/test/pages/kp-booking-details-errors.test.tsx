import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingDetails from "../../pages/KpBookingDetails";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testBookingId, testEventId } from "../fixtures/kp-booking";
import { emptyVenueHandler } from "../fixtures/venue";

const detailsPath = "/kp/:id/bookings/:bookingId";
const detailsRoute = `/kp/${testEventId}/bookings/${testBookingId}`;

const renderDetails = () =>
  renderWithProviders(
    <Routes>
      <Route path={detailsPath} element={<KpBookingDetails />} />
    </Routes>,
    { route: detailsRoute },
  );

const failBookingWith = (status: number) =>
  server.use(
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
      () => HttpResponse.json({ statusCode: status }, { status }),
    ),
  );

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    emptyVenueHandler,
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
      () =>
        HttpResponse.json(
          {
            statusCode: 403,
            code: "error.not_allowed",
            identifier: "require_role",
            message: "User is not allowed to make this request",
          },
          { status: 403 },
        ),
    ),
    http.get(
      `${testBackendUrl}/api/kp/staff/events/:eventId/bookings/:bookingId/requirement-files`,
      () => HttpResponse.json({ files: {} }),
    ),
  );
});

describe("KpBookingDetails without the president role", () => {
  it("explains the missing permission instead of claiming not found", async () => {
    renderDetails();

    expect(
      await screen.findByText(
        "kp.manage.booking_detail_forbidden",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.manage.booking_detail_not_found"),
    ).not.toBeInTheDocument();
  });
});

describe("KpBookingDetails when the booking fails to load", () => {
  it("reports a server error as a failed load, not as not found", async () => {
    failBookingWith(500);
    renderDetails();

    expect(
      await screen.findByText("error.load_failed", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.manage.booking_detail_not_found"),
    ).not.toBeInTheDocument();
  });

  it("says not found for a missing booking", async () => {
    failBookingWith(404);
    renderDetails();

    expect(
      await screen.findByText(
        "kp.manage.booking_detail_not_found",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
  });
});
