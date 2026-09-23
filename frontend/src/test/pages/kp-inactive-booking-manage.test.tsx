import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingConfirmation from "../../pages/KpBookingConfirmation";
import KpBookingManage from "../../pages/KpBookingManage";
import KpBookingManageOverview from "../../pages/KpBookingManageOverview";
import type { BookingResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testCancelledBooking,
  testEventId,
  testOpenEvent,
  testRejectedBooking,
} from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const FIND_TIMEOUT = SLOW_WAIT;
const landingTestId = "company-view-landing";

let myBooking: BookingResponse = testBooking;

const renderOverview = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp/:id" element={<div data-testid={landingTestId} />} />
      <Route
        path="/kp/:id/booking/:bookingId/manage"
        element={<KpBookingManageOverview />}
      />
    </Routes>,
    { route: `/kp/${testEventId}/booking/${testBookingId}/manage` },
  );

const renderConfirmation = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp/:id" element={<div data-testid={landingTestId} />} />
      <Route
        path="/kp/:id/booking/:bookingId"
        element={<KpBookingConfirmation />}
      />
    </Routes>,
    { route: `/kp/${testEventId}/booking/${testBookingId}` },
  );

const renderServices = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp/:id" element={<div data-testid={landingTestId} />} />
      <Route
        path="/kp/:id/booking/:bookingId/manage/services"
        element={<KpBookingManage />}
      />
    </Routes>,
    { route: `/kp/${testEventId}/booking/${testBookingId}/manage/services` },
  );

beforeEach(() => {
  myBooking = testBooking;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testOpenEvent),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(myBooking),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/bookings/:bookingId/nametags`, () =>
      HttpResponse.json([]),
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

describe("the booking confirmation page", () => {
  it("sends a rejected booking back to the company view", async () => {
    myBooking = testRejectedBooking;

    renderConfirmation();

    expect(
      await screen.findByTestId(landingTestId, undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
  });

  it("still renders an active booking", async () => {
    renderConfirmation();

    expect(
      await screen.findByRole(
        "heading",
        { name: /kp\.booking\.summary_title/ },
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
  });
});

describe("the booking manage overview", () => {
  it("sends a rejected booking back to the company view", async () => {
    myBooking = testRejectedBooking;

    renderOverview();

    expect(
      await screen.findByTestId(landingTestId, undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
  });

  it("sends a cancelled booking back to the company view", async () => {
    myBooking = testCancelledBooking;

    renderOverview();

    expect(
      await screen.findByTestId(landingTestId, undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
  });

  it("still renders an active booking", async () => {
    renderOverview();

    expect(
      await screen.findByText(
        "kp.booking_manage.title",
        undefined,
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
  });
});

describe("the booking services page", () => {
  it("sends a rejected booking back to the company view", async () => {
    myBooking = testRejectedBooking;

    renderServices();

    expect(
      await screen.findByTestId(landingTestId, undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
  });

  it("sends a cancelled booking back to the company view", async () => {
    myBooking = testCancelledBooking;

    renderServices();

    expect(
      await screen.findByTestId(landingTestId, undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
  });

  it("still renders an active booking", async () => {
    renderServices();

    expect(
      await screen.findByText(
        "kp.booking_manage.services_page_title",
        undefined,
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
  });
});
