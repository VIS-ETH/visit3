import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingStepper from "../../pages/KpBookingStepper";
import KpCompanyView from "../../pages/KpCompanyView";
import type {
  BookingResponse,
  MyBookingResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { installCompanyProfileHandlers } from "../fixtures/company-profile";
import {
  testBooking,
  testCancelledBooking,
  testEventId,
  testOpenEvent,
  testRejectedBooking,
} from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const FIND_TIMEOUT = SLOW_WAIT;

const rejectedBookingWithoutNewRegistration: MyBookingResponse = {
  ...testRejectedBooking,
  can_register: false,
};

let myBooking: BookingResponse = testBooking;

const companyViewRoute = `/kp/${testEventId}`;

const renderCompanyView = () =>
  renderWithProviders(
    <Routes>
      <Route path="/kp/:id" element={<KpCompanyView />} />
    </Routes>,
    { route: companyViewRoute },
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
      `${testBackendUrl}/api/kp/events/:eventId/booth-zones/available`,
      () => HttpResponse.json([]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([]),
    ),
  );
  installCompanyProfileHandlers();
});

describe("the company view with a rejected booking", () => {
  it("explains the rejection and offers a new booking", async () => {
    myBooking = testRejectedBooking;

    renderCompanyView();

    expect(
      await screen.findByText(
        "kp.booking.rejected_title",
        undefined,
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Zone already assigned to another company"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "kp.company_view.restart_booking" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.company_view.manage_booking" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.booking.cancel_action" }),
    ).not.toBeInTheDocument();
  });

  it("hides the new booking button when can_register is false", async () => {
    myBooking = rejectedBookingWithoutNewRegistration;

    renderCompanyView();

    expect(
      await screen.findByText(
        "kp.booking.rejected_title",
        undefined,
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.company_view.restart_booking" }),
    ).not.toBeInTheDocument();
  });
});

describe("the company view with a cancelled booking", () => {
  it("shows the cancellation notice without a new booking button", async () => {
    myBooking = testCancelledBooking;

    renderCompanyView();

    expect(
      await screen.findByText(
        "kp.booking.cancelled_title",
        undefined,
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.company_view.inactive_booking_hint"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.company_view.restart_booking" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.company_view.manage_booking" }),
    ).not.toBeInTheDocument();
  });
});

describe("the company view with an active booking", () => {
  it("keeps the manage action and the completeness section", async () => {
    renderCompanyView();

    expect(
      await screen.findByRole(
        "button",
        { name: "kp.company_view.manage_booking" },
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking.completeness_incomplete"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.company_view.restart_booking" }),
    ).not.toBeInTheDocument();
  });
});

describe("the booking wizard with an inactive booking", () => {
  it("does not treat a rejected booking as an existing booking", async () => {
    myBooking = testRejectedBooking;

    renderWithProviders(<KpBookingStepper event={testOpenEvent} />);

    expect(
      await screen.findByText(
        "kp.booking.profile_title",
        undefined,
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.booking.already_booked_notice"),
    ).not.toBeInTheDocument();
  });

  it("still blocks a second booking while one is active", async () => {
    renderWithProviders(<KpBookingStepper event={testOpenEvent} />);

    expect(
      await screen.findByText(
        "kp.booking.already_booked_notice",
        undefined,
        FIND_TIMEOUT,
      ),
    ).toBeInTheDocument();
  });
});
