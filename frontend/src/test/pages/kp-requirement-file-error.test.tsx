import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import KpBookingDetails from "../../pages/KpBookingDetails";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEvent,
  testEventId,
  testStaffBooking,
} from "../fixtures/kp-booking";
import { emptyVenueHandler } from "../fixtures/venue";

let requirementFileRequests = 0;
let staffRequirementFileRequests = 0;

const managePath = "/kp/:id/booking/:bookingId/manage/services";
const detailsPath = "/kp/:id/bookings/:bookingId";

beforeEach(() => {
  requirementFileRequests = 0;
  staffRequirementFileRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    emptyVenueHandler,
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testEvent),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(testBooking),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/text`,
      () => HttpResponse.json(null),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
      () => {
        requirementFileRequests += 1;
        return HttpResponse.json(
          { statusCode: 500, code: "server.error" },
          { status: 500 },
        );
      },
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
      () => HttpResponse.json(testStaffBooking),
    ),
    http.get(
      `${testBackendUrl}/api/kp/staff/events/:eventId/bookings/:bookingId/requirement-files`,
      () => {
        staffRequirementFileRequests += 1;
        return HttpResponse.json(
          { statusCode: 500, code: "server.error" },
          { status: 500 },
        );
      },
    ),
  );
});

describe("requirement file load errors", () => {
  it("reports a failed lookup instead of offering an upload", async () => {
    const { user } = renderWithProviders(
      <Routes>
        <Route path={managePath} element={<KpBookingManage />} />
      </Routes>,
      { route: `/kp/${testEventId}/booking/${testBookingId}/manage/services` },
    );

    expect(
      await screen.findByText(
        "kp.booking_manage.file_load_error",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.booking_manage.no_file"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText("kp.booking_manage.upload_file"),
    ).not.toBeInTheDocument();

    const requestsBeforeRetry = requirementFileRequests;
    await user.click(
      screen.getByRole("button", { name: "kp.booking_manage.retry_file_load" }),
    );

    await waitFor(() => {
      expect(requirementFileRequests).toBeGreaterThan(requestsBeforeRetry);
    });
  });

  it("reports a failed staff lookup with a retry action", async () => {
    const { user } = renderWithProviders(
      <Routes>
        <Route path={detailsPath} element={<KpBookingDetails />} />
      </Routes>,
      { route: `/kp/${testEventId}/bookings/${testBookingId}` },
    );

    const alert = await screen.findByRole("alert", {}, { timeout: 5000 });
    expect(
      within(alert).getByText("kp.manage.booking_requirement_load_error"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.manage.booking_requirement_missing_badge"),
    ).not.toBeInTheDocument();

    const requestsBeforeRetry = staffRequirementFileRequests;
    await user.click(
      screen.getByRole("button", {
        name: "kp.manage.booking_requirement_retry",
      }),
    );

    await waitFor(() => {
      expect(staffRequirementFileRequests).toBeGreaterThan(requestsBeforeRetry);
    });
  });
});
