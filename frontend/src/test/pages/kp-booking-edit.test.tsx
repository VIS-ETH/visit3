import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingDetails from "../../pages/KpBookingDetails";
import type { StaffUpdateBookingRequest } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { notificationsShow } from "../notifications";
import {
  testEventId,
  testServiceId,
  testStaffBooking,
} from "../fixtures/kp-booking";
import { emptyVenueHandler } from "../fixtures/venue";
import {
  acmeBooking,
  acmeBookingId,
  staffBookings,
  testMainHallZone,
  testSideHallZone,
  testSideHallZoneId,
} from "../fixtures/staff-bookings";

const detailsPath = "/kp/:id/bookings/:bookingId";
const detailsRoute = `/kp/${testEventId}/bookings/${acmeBookingId}`;

const bookedService = testStaffBooking.services?.[0].service;
const extraServiceId = "cccc0000-0000-0000-0000-000000000001";
const extraService = {
  ...bookedService,
  id: extraServiceId,
  name: "Extra chairs",
  price: 2500,
  requirements: [],
};

const patches: StaffUpdateBookingRequest[] = [];

const servePatch = (response?: { status: number; code: string }) => {
  server.use(
    http.patch(
      `${testBackendUrl}/api/kp/bookings/:bookingId`,
      async ({ request }) => {
        patches.push((await request.json()) as StaffUpdateBookingRequest);
        if (response) {
          return HttpResponse.json(
            {
              statusCode: response.status,
              code: response.code,
              identifier: "update_booking",
              message: response.code,
            },
            { status: response.status },
          );
        }
        return HttpResponse.json(acmeBooking);
      },
    ),
  );
};

const renderDetails = () =>
  renderWithProviders(
    <Routes>
      <Route path={detailsPath} element={<KpBookingDetails />} />
    </Routes>,
    { route: detailsRoute },
  );

const saveButton = () =>
  screen.getByRole("button", { name: "kp.manage.booking_edit_save" });

const waitForPanel = () =>
  screen.findByText("kp.manage.booking_edit_title", {}, { timeout: 5000 });

beforeEach(() => {
  patches.length = 0;
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
    http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
      HttpResponse.json(staffBookings),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/booth-zones`, () =>
      HttpResponse.json([testMainHallZone, testSideHallZone]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/services`, () =>
      HttpResponse.json([bookedService, extraService]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/staff/events/:eventId/bookings/:bookingId/requirement-files`,
      () => HttpResponse.json({ files: {} }),
    ),
  );
});

describe("the staff booking edit panel", () => {
  it("sends only the fields that changed", async () => {
    servePatch();
    const { user } = renderDetails();

    await waitForPanel();
    const note = screen.getByLabelText("kp.manage.booking_edit_status_note");
    await user.type(note, "Moved to the window side.");
    await user.click(saveButton());

    await waitFor(() =>
      expect(patches).toEqual([{ status_note: "Moved to the window side." }]),
    );
  });

  it("sends the new zone and booth number together", async () => {
    servePatch();
    const { user } = renderDetails();

    await waitForPanel();
    await user.click(
      screen.getByRole("combobox", { name: "kp.manage.booking_edit_zone" }),
    );
    await user.click(await screen.findByText("Side hall"));
    const boothNr = screen.getByRole("textbox", {
      name: "kp.manage.booking_edit_booth_nr",
    });
    await user.clear(boothNr);
    await user.type(boothNr, "9");
    await user.click(saveButton());

    await waitFor(() =>
      expect(patches).toEqual([
        { booth_zone_id: testSideHallZoneId, booth_nr: 9 },
      ]),
    );
  });

  it("shows the free spots of every zone", async () => {
    const { user } = renderDetails();

    await waitForPanel();
    await user.click(
      screen.getByRole("combobox", { name: "kp.manage.booking_edit_zone" }),
    );

    expect(
      await screen.findAllByText("kp.manage.booking_edit_zone_availability"),
    ).toHaveLength(2);
  });

  it("sends only the service whose quantity changed", async () => {
    servePatch();
    const { user } = renderDetails();

    await waitForPanel();
    const quantity = screen.getByRole("textbox", { name: "Booth package" });
    await user.clear(quantity);
    await user.type(quantity, "3");
    await user.click(saveButton());

    await waitFor(() =>
      expect(patches).toEqual([
        { services: [{ service_id: testServiceId, quantity: 3 }] },
      ]),
    );
  });

  it("removes a service when its quantity goes to zero", async () => {
    servePatch();
    const { user } = renderDetails();

    await waitForPanel();
    const quantity = screen.getByRole("textbox", { name: "Booth package" });
    await user.clear(quantity);
    await user.type(quantity, "0");
    await user.click(saveButton());

    await waitFor(() =>
      expect(patches).toEqual([
        { services: [{ service_id: testServiceId, quantity: 0 }] },
      ]),
    );
  });

  it("books a service the company had not picked", async () => {
    servePatch();
    const { user } = renderDetails();

    await waitForPanel();
    await user.click(
      screen.getByRole("combobox", {
        name: "kp.manage.booking_edit_add_service",
      }),
    );
    await user.click(await screen.findByText("Extra chairs"));
    await user.click(saveButton());

    await waitFor(() =>
      expect(patches).toEqual([
        { services: [{ service_id: extraServiceId, quantity: 1 }] },
      ]),
    );
  });

  it("says so instead of sending an empty patch", async () => {
    servePatch();
    const { user } = renderDetails();

    await waitForPanel();
    await user.click(saveButton());

    await waitFor(() =>
      expect(notificationsShow).toHaveBeenCalledWith({
        color: "blue",
        message: "kp.manage.booking_edit_no_changes",
      }),
    );
    expect(patches).toEqual([]);
  });

  it("puts a full zone on the zone field", async () => {
    servePatch({ status: 409, code: "error.kp_booth_zone_full" });
    const { user } = renderDetails();

    await waitForPanel();
    await user.click(
      screen.getByRole("combobox", { name: "kp.manage.booking_edit_zone" }),
    );
    await user.click(await screen.findByText("Side hall"));
    await user.click(saveButton());

    expect(
      await screen.findByText("error.kp_booth_zone_full"),
    ).toBeInTheDocument();
  });

  it("puts a taken booth number on the booth number field", async () => {
    servePatch({ status: 409, code: "error.kp_booth_number_taken" });
    const { user } = renderDetails();

    await waitForPanel();
    const boothNr = screen.getByRole("textbox", {
      name: "kp.manage.booking_edit_booth_nr",
    });
    await user.clear(boothNr);
    await user.type(boothNr, "9");
    await user.click(saveButton());

    expect(
      await screen.findByText("error.kp_booth_number_taken"),
    ).toBeInTheDocument();
  });

  it("puts an impossible quantity next to the services", async () => {
    servePatch({ status: 409, code: "error.kp_service_quantity_invalid" });
    const { user } = renderDetails();

    await waitForPanel();
    const quantity = screen.getByRole("textbox", { name: "Booth package" });
    await user.clear(quantity);
    await user.type(quantity, "5");
    await user.click(saveButton());

    expect(
      await screen.findByText("error.kp_service_quantity_invalid"),
    ).toBeInTheDocument();
  });
});
