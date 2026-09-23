import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingDetails from "../../pages/KpBookingDetails";
import type { NameTagResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import i18n from "../i18n";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { emptyVenueHandler } from "../fixtures/venue";
import { acmeBooking, acmeBookingId } from "../fixtures/staff-bookings";

const detailsPath = "/kp/:id/bookings/:bookingId";
const detailsRoute = `/kp/${testEventId}/bookings/${acmeBookingId}`;
const staffNametagsUrl = `${testBackendUrl}/api/kp/staff/bookings/${acmeBookingId}/nametags`;

const acmeNametags: NameTagResponse[] = [
  {
    id: "aaaa1111-aaaa-1111-aaaa-111111111111",
    booking_id: acmeBookingId,
    first_name: "Marie",
    last_name: "Curie",
    position: "Recruiting",
  },
  {
    id: "bbbb2222-bbbb-2222-bbbb-222222222222",
    booking_id: acmeBookingId,
    first_name: "Leonhard",
    last_name: "Euler",
    position: "Engineering",
  },
];

const renderDetails = () =>
  renderWithProviders(
    <Routes>
      <Route path={detailsPath} element={<KpBookingDetails />} />
    </Routes>,
    { route: detailsRoute },
  );

beforeAll(() => {
  i18n.addResource(
    "en",
    "common",
    "kp.nametags.staff_count",
    "{{total}} nametags",
  );
});

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    emptyVenueHandler,
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/bookings/:bookingId`,
      () => HttpResponse.json(acmeBooking),
    ),
    http.get(
      `${testBackendUrl}/api/kp/staff/events/:eventId/bookings/:bookingId/requirement-files`,
      () => HttpResponse.json({ files: {} }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/booth-zones`, () =>
      HttpResponse.json([]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/services`, () =>
      HttpResponse.json([]),
    ),
  );
});

describe("the staff booking nametag card", () => {
  it("lists every nametag of the booking with its count", async () => {
    server.use(
      http.get(staffNametagsUrl, () => HttpResponse.json(acmeNametags)),
    );

    renderDetails();

    expect(
      await screen.findByText("kp.nametags.staff_title", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(await screen.findByText("2 nametags")).toBeInTheDocument();
    expect(screen.getByText("Curie")).toBeInTheDocument();
    expect(screen.getByText("Recruiting")).toBeInTheDocument();
    expect(screen.getByText("Euler")).toBeInTheDocument();
    expect(screen.getByText("Engineering")).toBeInTheDocument();
  });

  it("says when the booking has no nametags", async () => {
    server.use(http.get(staffNametagsUrl, () => HttpResponse.json([])));

    renderDetails();

    expect(
      await screen.findByText("kp.nametags.staff_empty", {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByText("0 nametags")).toBeInTheDocument();
  });

  it("reports a failed nametag load", async () => {
    server.use(
      http.get(staffNametagsUrl, () =>
        HttpResponse.json({ code: "server.error" }, { status: 500 }),
      ),
    );

    renderDetails();

    expect(
      await screen.findByText(
        "kp.nametags.staff_load_error",
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
  });
});
