import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import KpBookingStepper from "../../pages/KpBookingStepper";
import {
  KpBookingStatus,
  KpServiceCategory,
} from "../../orval/generated/fastAPI.schemas";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  KpResponse,
  ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
import i18n from "../i18n";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  confirmProfileStep,
  installCompanyProfileHandlers,
} from "../fixtures/company-profile";
import { emptyVenueHandler } from "../fixtures/venue";
import {
  continueToBoothStep,
  continueToSummaryStep,
} from "../fixtures/booking-wizard";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const eventId = "event-1";
const tablePrice = 4000;
const chairPrice = 1500;
const includedChairs = 2;

const csrfUrl = `${testBackendUrl}/api/csrftoken`;
const myBookingUrl = `${testBackendUrl}/api/kp/events/${eventId}/my-booking`;
const zonesUrl = `${testBackendUrl}/api/kp/events/${eventId}/booth-zones/available`;
const servicesUrl = `${testBackendUrl}/api/kp/events/${eventId}/services/available`;
const registerUrl = `${testBackendUrl}/api/kp/events/${eventId}/bookings/register`;

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

const serviceDefaults = {
  event_id: eventId,
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  max_total_quantity: 0,
  remaining_total_quantity: null,
  is_active: true,
  requirements: [],
};

const powerSocket: ServiceResponse = {
  ...serviceDefaults,
  id: "service-power",
  name: "Power Socket",
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  price: 2500,
  max_quantity_per_booking: 3,
};

const table: ServiceResponse = {
  ...serviceDefaults,
  id: "booth-table",
  name: "Tisch",
  category: KpServiceCategory.BOOTH_ELEMENT,
  unit_label: "Stück",
  price: tablePrice,
  max_quantity_per_booking: 4,
};

const chair: ServiceResponse = {
  ...serviceDefaults,
  id: "booth-chair",
  name: "Stuhl",
  category: KpServiceCategory.BOOTH_ELEMENT,
  unit_label: "Stück",
  price: chairPrice,
  max_quantity_per_booking: 6,
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
  layout_description: "Two metre wide corner booth",
  layout_url: "https://files.test/zone-1/layout.png",
  included_services: [
    { service_id: chair.id, included_quantity: includedChairs },
  ],
  is_full: false,
};

const registeredBooking: BookingResponse = {
  id: "booking-1",
  booking_number: 1,
  event_id: eventId,
  company_id: "company-1",
  booth_zone_id: zone.id,
  booth_nr: null,
  status: KpBookingStatus.REGISTERED,
  services: [],
  price: { net: 0, vat: 0, gross: 0 },
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

const boothQuantityInputs = () =>
  screen.getAllByLabelText<HTMLInputElement>("Quantity (Stück)");

beforeAll(() => {
  i18n.addResource(
    "en",
    "common",
    "kp.booking.service_included_note",
    "{{included}} included",
  );
  i18n.addResource(
    "en",
    "common",
    "kp.booking.service_quantity_with_unit",
    "Quantity ({{unit}})",
  );
});

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    emptyVenueHandler,
    http.get(csrfUrl, () => HttpResponse.json({ token: "csrf-1" })),
    http.get(myBookingUrl, () => HttpResponse.json(null)),
    http.get(zonesUrl, () => HttpResponse.json([zone])),
    http.get(servicesUrl, () => HttpResponse.json([powerSocket, table, chair])),
  );
});

describe("the booth step of the booking wizard", () => {
  it("keeps booth elements out of the services step", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);

    expect(screen.getByText(powerSocket.name)).toBeInTheDocument();
    expect(screen.queryByText(table.name)).not.toBeInTheDocument();
    expect(screen.queryByText(chair.name)).not.toBeInTheDocument();
  });

  it("lists only booth elements with their unit and inclusions", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);
    await continueToBoothStep(user);

    expect(screen.getByText(table.name)).toBeInTheDocument();
    expect(screen.getByText(chair.name)).toBeInTheDocument();
    expect(screen.queryByText(powerSocket.name)).not.toBeInTheDocument();
    expect(screen.getByText("2 included")).toBeInTheDocument();
    expect(boothQuantityInputs()).toHaveLength(2);
    expect(
      screen.queryByText(zone.layout_description as string),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("starts the included booth element at its included quantity", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);
    await continueToBoothStep(user);

    const [tableInput, chairInput] = boothQuantityInputs();
    expect(tableInput).toHaveValue("0");
    expect(chairInput).toHaveValue(String(includedChairs));
  });

  it("groups the summary lines and totals both categories", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);
    const socketInput = screen.getByLabelText("kp.booking.service_quantity");
    await user.clear(socketInput);
    await user.type(socketInput, "2");
    await continueToBoothStep(user);
    const [tableInput] = boothQuantityInputs();
    await user.clear(tableInput);
    await user.type(tableInput, "1");
    await user.click(
      screen.getByRole("button", { name: "kp.booking.continue_to_summary" }),
    );
    await screen.findByText("kp.booking.summary_title", undefined, SLOW_WAIT);

    expect(
      screen.getByText("kp.booking.summary_group_services"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking.summary_group_booth_elements"),
    ).toBeInTheDocument();
    expect(screen.getByText("Power Socket × 2")).toBeInTheDocument();
    expect(screen.getByText("Tisch")).toBeInTheDocument();
    expect(screen.getByText("Stuhl (2 included)")).toBeInTheDocument();
    expect(screen.getByText("CHF 1090.00")).toBeInTheDocument();
  });

  it("registers the booth elements together with the services", async () => {
    let registered: unknown = null;
    server.use(
      http.post(registerUrl, async ({ request }) => {
        registered = await request.json();
        return HttpResponse.json(registeredBooking);
      }),
    );
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);
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
        services: [{ service_id: chair.id, quantity: includedChairs }],
      });
    }, SLOW_WAIT);
  });
});
