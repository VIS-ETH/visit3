import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import App from "../../App";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBookingId,
  testEventId,
  testStaffBooking,
} from "../fixtures/kp-booking";

const detailsRoute = `/kp/${testEventId}/bookings/${testBookingId}`;
const serviceFormRoute = `/kp/${testEventId}/services/new`;

const staffUser: UserResponse = {
  id: "staff-1",
  email: "staff@example.com",
  is_staff: true,
  is_admin: false,
  is_company: false,
  is_kp_president: false,
  user_confirmed: true,
  email_confirmed: true,
};

const presidentUser: UserResponse = {
  ...staffUser,
  id: "president-1",
  email: "president@example.com",
  is_kp_president: true,
};

const companyUser: UserResponse = {
  ...staffUser,
  id: "company-1",
  email: "company@example.com",
  is_staff: false,
};

const mockCurrentUser = (user: UserResponse) => {
  server.use(
    http.get(`${testBackendUrl}/api/user/me`, () => HttpResponse.json(user)),
  );
};

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.post(`${testBackendUrl}/api/auth/refresh`, () =>
      HttpResponse.json({ access_token: createToken(3600) }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
      () => HttpResponse.json(testStaffBooking),
    ),
    http.get(
      `${testBackendUrl}/api/kp/staff/events/:eventId/bookings/:bookingId/requirement-files`,
      () => HttpResponse.json({ files: {} }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/staff/bookings/:bookingId/nametags`,
      () => HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/services`, () =>
      HttpResponse.json([]),
    ),
  );
});

describe("the KP booking detail route guard", () => {
  it("lets staff without the president role open the booking details", async () => {
    mockCurrentUser(staffUser);

    renderWithProviders(<App />, { route: detailsRoute });

    expect(
      await screen.findByText(
        "kp.manage.booking_detail_title",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("not_allowed.title")).not.toBeInTheDocument();
  });

  it("lets a president open the booking details", async () => {
    mockCurrentUser(presidentUser);

    renderWithProviders(<App />, { route: detailsRoute });

    expect(
      await screen.findByText(
        "kp.manage.booking_detail_title",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("not_allowed.title")).not.toBeInTheDocument();
  });

  it("sends a user who is neither staff nor president to the explanation page", async () => {
    mockCurrentUser(companyUser);

    renderWithProviders(<App />, { route: detailsRoute });

    expect(
      await screen.findByText("not_allowed.title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.manage.booking_detail_title"),
    ).not.toBeInTheDocument();
  });
});

describe("the KP president route guard", () => {
  it("keeps the event configuration away from plain staff", async () => {
    mockCurrentUser(staffUser);

    renderWithProviders(<App />, { route: serviceFormRoute });

    expect(
      await screen.findByText("not_allowed.title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  it("lets a president open the event configuration", async () => {
    mockCurrentUser(presidentUser);

    renderWithProviders(<App />, { route: serviceFormRoute });

    expect(
      await screen.findByText("kp.manage.services_add", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.queryByText("not_allowed.title")).not.toBeInTheDocument();
  });
});
