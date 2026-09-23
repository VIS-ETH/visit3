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

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    emptyVenueHandler,
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
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
    renderWithProviders(
      <Routes>
        <Route path={detailsPath} element={<KpBookingDetails />} />
      </Routes>,
      { route: detailsRoute },
    );

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
