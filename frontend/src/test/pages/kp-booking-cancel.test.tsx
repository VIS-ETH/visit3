import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import type { BookingResponse } from "../../orval/generated/fastAPI.schemas";
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
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const completeBooking: BookingResponse = {
  ...testBooking,
  is_complete: true,
  missing_items: [],
};

const statusUrl = `${testBackendUrl}/api/kp/bookings/${testBookingId}/status`;
const managePath = "/kp/:id/booking/:bookingId/manage/services";
const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;

let bookingResponse: BookingResponse = completeBooking;

const companyViewTestId = "company-view-landing";

const renderManage = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp/:id" element={<div data-testid={companyViewTestId} />} />
      <Route path={managePath} element={<KpBookingManage />} />
    </Routes>,
    { route: manageRoute },
  );

const cancelButton = () =>
  screen.findByRole("button", { name: "kp.booking.cancel_action" }, SLOW_WAIT);

beforeEach(() => {
  bookingResponse = completeBooking;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testEvent),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(bookingResponse),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
      () => HttpResponse.json(null),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/text`,
      () => HttpResponse.json({ text_value: "" }),
    ),
  );
});

describe("cancelling a booking", () => {
  it("explains the consequences before cancelling", async () => {
    let statusRequests = 0;
    server.use(
      http.patch(statusUrl, () => {
        statusRequests += 1;
        return HttpResponse.json(completeBooking);
      }),
    );
    const { user } = renderManage();

    await user.click(await cancelButton());

    expect(
      screen.getByText("kp.booking.cancel_confirm_body"),
    ).toBeInTheDocument();
    expect(statusRequests).toBe(0);
  });

  it("keeps the booking when the confirmation is dismissed", async () => {
    let statusRequests = 0;
    server.use(
      http.patch(statusUrl, () => {
        statusRequests += 1;
        return HttpResponse.json(completeBooking);
      }),
    );
    const { user } = renderManage();

    await user.click(await cancelButton());
    await user.click(
      screen.getByRole("button", { name: "kp.booking.cancel_confirm_keep" }),
    );

    expect(statusRequests).toBe(0);
    expect(
      screen.queryByText("kp.booking.cancel_confirm_body"),
    ).not.toBeInTheDocument();
  });

  it("sends the cancelled status once the modal is confirmed", async () => {
    let payload: unknown = null;
    server.use(
      http.patch(statusUrl, async ({ request }) => {
        payload = await request.json();
        return HttpResponse.json({
          ...completeBooking,
          status: KpBookingStatus.CANCELLED,
        });
      }),
    );
    const { user } = renderManage();

    await user.click(await cancelButton());
    await user.click(
      screen.getByRole("button", { name: "kp.booking.cancel_confirm_submit" }),
    );

    await waitFor(() => {
      expect(payload).toEqual({ status: "CANCELLED" });
    }, SLOW_WAIT);
    await waitFor(() => {
      expect(
        screen.queryByText("kp.booking.cancel_confirm_body"),
      ).not.toBeInTheDocument();
    }, SLOW_WAIT);
  });

  it("hides the action for a cancelled booking", async () => {
    bookingResponse = {
      ...completeBooking,
      status: KpBookingStatus.CANCELLED,
    };
    renderManage();

    await screen.findByTestId(companyViewTestId, undefined, SLOW_WAIT);
    expect(
      screen.queryByRole("button", { name: "kp.booking.cancel_action" }),
    ).not.toBeInTheDocument();
  });
});
