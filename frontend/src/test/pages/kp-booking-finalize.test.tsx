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
  testFileRequirementId,
} from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const completeBooking: BookingResponse = {
  ...testBooking,
  is_complete: true,
  missing_items: [],
};

const incompleteBooking: BookingResponse = {
  ...testBooking,
  is_complete: false,
  missing_items: [`requirement:${testFileRequirementId}`],
};

const statusUrl = `${testBackendUrl}/api/kp/bookings/${testBookingId}/status`;
const managePath = "/kp/:id/booking/:bookingId/manage/services";
const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;

let bookingResponse: BookingResponse = completeBooking;

const renderManage = () =>
  renderWithProviders(
    <Routes>
      <Route path={managePath} element={<KpBookingManage />} />
    </Routes>,
    { route: manageRoute },
  );

const finalizeButton = () =>
  screen.findByRole(
    "button",
    { name: "kp.booking.finalize_action" },
    SLOW_WAIT,
  );

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

describe("finalizing a booking", () => {
  it("keeps the action disabled while the booking is incomplete", async () => {
    bookingResponse = incompleteBooking;
    renderManage();

    expect(await finalizeButton()).toBeDisabled();
    expect(
      screen.getByText("kp.booking.completeness_incomplete"),
    ).toBeInTheDocument();
  });

  it("asks for confirmation and sends the finalized status", async () => {
    let statusRequests = 0;
    let payload: unknown = null;
    server.use(
      http.patch(statusUrl, async ({ request }) => {
        statusRequests += 1;
        payload = await request.json();
        return HttpResponse.json({
          ...completeBooking,
          status: KpBookingStatus.FINALIZED,
        });
      }),
    );
    const { user } = renderManage();

    await user.click(await finalizeButton());
    expect(
      screen.getByText("kp.booking.finalize_confirm_body"),
    ).toBeInTheDocument();
    expect(statusRequests).toBe(0);

    await user.click(
      screen.getByRole("button", {
        name: "kp.booking.finalize_confirm_submit",
      }),
    );

    await waitFor(() => {
      expect(statusRequests).toBe(1);
    }, SLOW_WAIT);
    expect(payload).toEqual({ status: "FINALIZED" });
    await waitFor(() => {
      expect(
        screen.queryByText("kp.booking.finalize_confirm_body"),
      ).not.toBeInTheDocument();
    }, SLOW_WAIT);
  });

  it("lists the blocking items when the backend rejects the finalization", async () => {
    server.use(
      http.patch(statusUrl, () =>
        HttpResponse.json(
          {
            statusCode: 409,
            code: "error.kp_booking_incomplete",
            details: {
              missingItems: [
                `requirement:${testFileRequirementId}`,
                "billing_address",
              ],
            },
          },
          { status: 409 },
        ),
      ),
    );
    const { user } = renderManage();

    await user.click(await finalizeButton());
    await user.click(
      screen.getByRole("button", {
        name: "kp.booking.finalize_confirm_submit",
      }),
    );

    expect(
      await screen.findByText(
        "error.kp_booking_incomplete",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Booth package · Company brochure"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "kp.booking.missing_item_billing_address",
      }),
    ).toBeInTheDocument();
  });

  it("hides the action once the booking is finalized", async () => {
    bookingResponse = {
      ...completeBooking,
      status: KpBookingStatus.FINALIZED,
    };
    renderManage();

    expect(
      await screen.findByText("kp.booking.finalized_title", {}, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.booking.finalize_action" }),
    ).not.toBeInTheDocument();
  });
});
