import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpManage from "../../pages/KpManage";
import { UserProvider } from "../../context/UserContext";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEvent, testEventId } from "../fixtures/kp-booking";

const PRESIDENT_TABS = [
  "kp.manage.tab_services",
  "kp.manage.tab_booth_zones",
  "kp.venue.tab_title",
  "kp.manage.tab_industries",
];

const STAFF_TABS = [
  "kp.manage.tab_details",
  "kp.manage.tab_exports",
  "kp.manage.tab_bookings",
];

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

const renderManage = (user: UserResponse) =>
  renderWithProviders(
    <UserProvider user={user} isLoading={false}>
      <Routes>
        <Route path="/kp/:id" element={<KpManage />} />
      </Routes>
    </UserProvider>,
    { route: `/kp/${testEventId}` },
  );

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testEvent),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/settings`, () =>
      HttpResponse.json({ ...testEvent, notification_email: null }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/background`,
      () => HttpResponse.json(null),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/exports/nametags/targets`,
      () => HttpResponse.json({ companies: [], people: [] }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/services`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/booth-zones`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/venue-layouts`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
      HttpResponse.json([]),
    ),
  );
});

describe("the KP management tabs", () => {
  it("hides the configuration tabs from plain staff", async () => {
    renderManage(staffUser);

    expect(
      await screen.findByText("kp.manage.tab_exports", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    for (const tab of PRESIDENT_TABS) {
      expect(screen.queryByText(tab)).not.toBeInTheDocument();
    }
  });

  it("shows the bookings tab to plain staff", async () => {
    renderManage(staffUser);

    for (const tab of STAFF_TABS) {
      expect(
        await screen.findByText(tab, {}, { timeout: 5000 }),
      ).toBeInTheDocument();
    }
  });

  it("shows the configuration tabs to a president", async () => {
    renderManage(presidentUser);

    expect(
      await screen.findByText("kp.manage.tab_exports", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    for (const tab of [...STAFF_TABS, ...PRESIDENT_TABS]) {
      expect(screen.getByText(tab)).toBeInTheDocument();
    }
  });
});
