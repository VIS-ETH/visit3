import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import KpBookingStepper from "../../pages/KpBookingStepper";
import { KpServiceCategory } from "../../orval/generated/fastAPI.schemas";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  KpResponse,
  ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  confirmProfileStep,
  installCompanyProfileHandlers,
} from "../fixtures/company-profile";
import {
  testBooking,
  testBookingId,
  testEvent,
  testEventId,
} from "../fixtures/kp-booking";
import { continueToSummaryStep } from "../fixtures/booking-wizard";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const eventId = "event-1";

const event: KpResponse = {
  id: eventId,
  name: "KP",
  registration_open: "2000-01-01",
  registration_end: "2099-12-31",
  finalization_deadline: "2099-12-31",
  nametags_deadline: "2099-12-31",
  event_date: "2099-12-31",
  vat_rate_percent: 8.1,
  terms_url: null,
  finalization_reminder_days: 3,
  max_nametags_per_booking: 5,
};

const zone: BoothZoneWithAvailabilityResponse = {
  id: "zone-1",
  event_id: eventId,
  name: "Main Hall",
  description: "",
  color: "#112233",
  order: 1,
  capacity: 10,
  booth_size: 4,
  base_price: 100000,
  included_services: [],
  available_spots: 3,
};

const singleService: ServiceResponse = {
  id: "service-single",
  event_id: eventId,
  name: "Nametag printing",
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  price: 5000,
  max_quantity_per_booking: 1,
  max_total_quantity: 0,
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  is_active: true,
  requirements: [],
};

const multiService: ServiceResponse = {
  ...singleService,
  id: "service-multi",
  name: "Power Socket",
  max_quantity_per_booking: 3,
};

const registeredBooking: BookingResponse = {
  id: "booking-1",
  booking_number: 1,
  event_id: eventId,
  company_id: "company-1",
  booth_zone_id: zone.id,
  booth_nr: null,
  status: "REGISTERED",
  services: [],
  price: { net: 105000, vat: 8505, gross: 113505 },
};

const openServicesStep = async (user: UserEvent) => {
  await confirmProfileStep(user);
  await user.click(
    await screen.findByRole(
      "button",
      { name: new RegExp(zone.name) },
      SLOW_WAIT,
    ),
  );
  await user.click(
    screen.getByRole("button", { name: "kp.booking.continue_with_zone" }),
  );
  await screen.findByText("kp.booking.services_title", undefined, SLOW_WAIT);
};

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/${eventId}/my-booking`, () =>
      HttpResponse.json(null),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/${eventId}/booth-zones/available`,
      () => HttpResponse.json([zone]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/${eventId}/services/available`,
      () => HttpResponse.json([singleService, multiService]),
    ),
  );
  installCompanyProfileHandlers();
});

describe("single quantity services in the booking wizard", () => {
  it("offers a switch instead of a quantity input", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);

    expect(screen.getAllByRole("switch")).toHaveLength(1);
    expect(
      screen.getAllByLabelText("kp.booking.service_quantity"),
    ).toHaveLength(1);
  });

  it("books exactly one unit when the switch is turned on", async () => {
    let registered: unknown = null;
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/events/${eventId}/bookings/register`,
        async ({ request }) => {
          registered = await request.json();
          return HttpResponse.json(registeredBooking);
        },
      ),
    );
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);
    const toggle = screen.getByRole("switch");
    await user.click(toggle);

    expect(toggle).toBeChecked();
    expect(
      screen.getByText("kp.booking.service_line_total"),
    ).toBeInTheDocument();

    await continueToSummaryStep(user);
    await user.click(
      screen.getByRole("checkbox", {
        name: /kp\.booking\.confirm_agb_checkbox/,
      }),
    );
    await user.click(
      screen.getByRole("checkbox", {
        name: /kp\.booking\.confirm_binding_checkbox/,
      }),
    );
    await user.click(
      screen.getByRole("button", {
        name: "kp.booking.summary_confirm_register",
      }),
    );

    await waitFor(() => {
      expect(registered).toEqual({
        booth_zone_id: zone.id,
        confirm_profile: true,
        services: [{ service_id: singleService.id, quantity: 1 }],
      });
    }, SLOW_WAIT);
  });

  it("clears the booked unit when the switch is turned off again", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);
    const toggle = screen.getByRole("switch");
    await user.click(toggle);
    await user.click(toggle);

    expect(toggle).not.toBeChecked();
    expect(
      screen.queryByText("kp.booking.service_line_total"),
    ).not.toBeInTheDocument();
  });
});

describe("single quantity services on the booking page", () => {
  const managePath = "/kp/:id/booking/:bookingId/manage/services";
  const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;

  beforeEach(() => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
        HttpResponse.json(testEvent),
      ),
      http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
        HttpResponse.json(testBooking),
      ),
      http.get(
        `${testBackendUrl}/api/kp/events/:eventId/services/available`,
        () => HttpResponse.json([{ ...singleService, event_id: testEventId }]),
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

  it("adds a single quantity service through the switch", async () => {
    let added: unknown = null;
    server.use(
      http.post(
        `${testBackendUrl}/api/kp/bookings/${testBookingId}/services`,
        async ({ request }) => {
          added = await request.json();
          return HttpResponse.json(testBooking);
        },
      ),
    );
    const { user } = renderWithProviders(
      <Routes>
        <Route path={managePath} element={<KpBookingManage />} />
      </Routes>,
      { route: manageRoute },
    );

    const toggle = await screen.findByRole(
      "switch",
      { name: "kp.booking.service_book_toggle" },
      SLOW_WAIT,
    );
    const submit = screen.getByRole("button", {
      name: "kp.booking_manage.add_services_submit",
    });
    expect(submit).toBeDisabled();

    await user.click(toggle);
    expect(submit).toBeEnabled();

    await user.click(submit);
    await user.click(
      await screen.findByRole(
        "button",
        {
          name: "kp.booking_manage.confirm_add_services_submit",
        },
        SLOW_WAIT,
      ),
    );

    await waitFor(() => {
      expect(added).toEqual({
        services: [{ service_id: singleService.id, quantity: 1 }],
      });
    }, SLOW_WAIT);
  });
});
