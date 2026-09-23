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
import { continueToSummaryStep } from "../fixtures/booking-wizard";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const eventId = "event-1";
const serviceId = "service-1";
const unitPriceCents = 2500;
const includedQuantity = 2;

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

const zoneDefaults = {
  event_id: eventId,
  description: "",
  color: "#112233",
  order: 1,
  capacity: 10,
  booth_size: 4,
  base_price: 100000,
  available_spots: 3,
};

const includedZone: BoothZoneWithAvailabilityResponse = {
  ...zoneDefaults,
  id: "zone-included",
  name: "Main Hall",
  included_services: [
    { service_id: serviceId, included_quantity: includedQuantity },
  ],
};

const plainZone: BoothZoneWithAvailabilityResponse = {
  ...zoneDefaults,
  id: "zone-plain",
  name: "Side Hall",
  included_services: [],
};

const service: ServiceResponse = {
  id: serviceId,
  event_id: eventId,
  name: "Power Socket",
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  price: unitPriceCents,
  max_quantity_per_booking: 5,
  max_total_quantity: 0,
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  remaining_total_quantity: null,
  is_active: true,
  requirements: [],
};

const registeredBooking: BookingResponse = {
  id: "booking-1",
  booking_number: 1,
  event_id: eventId,
  company_id: "company-1",
  booth_zone_id: includedZone.id,
  booth_nr: null,
  status: KpBookingStatus.REGISTERED,
  services: [],
  price: { net: 0, vat: 0, gross: 0 },
};

let availableServices: ServiceResponse[] = [service];

const quantityInput = () =>
  screen.getByLabelText<HTMLInputElement>("kp.booking.service_quantity");

const lineTotalText = () =>
  screen.getByText("kp.booking.service_line_total").parentElement?.textContent;

const openServicesStep = async (
  user: UserEvent,
  zone: BoothZoneWithAvailabilityResponse,
) => {
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

const backToZones = async (user: UserEvent) => {
  await user.click(
    screen.getByRole("button", { name: "kp.booking.stepper_back" }),
  );
  await screen.findByText("kp.booking.select_zone", undefined, SLOW_WAIT);
};

const acceptConsents = async (user: UserEvent) => {
  await user.click(
    screen.getByRole("checkbox", { name: /kp\.booking\.confirm_agb_checkbox/ }),
  );
  await user.click(
    screen.getByRole("checkbox", {
      name: /kp\.booking\.confirm_binding_checkbox/,
    }),
  );
};

const enterQuantity = async (user: UserEvent, typed: string) => {
  await user.clear(quantityInput());
  await user.type(quantityInput(), typed);
  return quantityInput().value;
};

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
    "kp.booking.service_remaining_total",
    "{{remaining}} still available",
  );
});

beforeEach(() => {
  availableServices = [service];
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    emptyVenueHandler,
    http.get(csrfUrl, () => HttpResponse.json({ token: "csrf-1" })),
    http.get(myBookingUrl, () => HttpResponse.json(null)),
    http.get(zonesUrl, () => HttpResponse.json([includedZone, plainZone])),
    http.get(servicesUrl, () => HttpResponse.json(availableServices)),
  );
});

describe("included services in the booking wizard", () => {
  it("seeds the included quantity and charges only the extra units", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await openServicesStep(user, includedZone);

    expect(quantityInput()).toHaveValue("2");
    expect(screen.getByText("2 included")).toBeInTheDocument();
    expect(lineTotalText()).toContain("CHF 0.00");

    expect(await enterQuantity(user, "3")).toBe("3");
    expect(lineTotalText()).toContain("CHF 25.00");

    await continueToSummaryStep(user);

    expect(screen.getByText("Power Socket (2 included)")).toBeInTheDocument();
    expect(screen.getByText("CHF 25.00")).toBeInTheDocument();
    expect(screen.getByText("CHF 1025.00")).toBeInTheDocument();
  });

  it("books the included minimum when a smaller quantity is entered", async () => {
    let registered: unknown = null;
    server.use(
      http.post(registerUrl, async ({ request }) => {
        registered = await request.json();
        return HttpResponse.json(registeredBooking);
      }),
    );
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await openServicesStep(user, includedZone);
    await enterQuantity(user, "1");
    await continueToSummaryStep(user);
    await acceptConsents(user);
    await user.click(
      screen.getByRole("button", {
        name: "kp.booking.summary_confirm_register",
      }),
    );

    await waitFor(() => {
      expect(registered).toEqual({
        booth_zone_id: includedZone.id,
        confirm_profile: true,
        services: [{ service_id: serviceId, quantity: includedQuantity }],
      });
    }, SLOW_WAIT);
  });

  it("drops the minimum back to zero for a zone without inclusions", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await openServicesStep(user, includedZone);
    expect(quantityInput()).toHaveValue("2");

    await backToZones(user);
    await openServicesStep(user, plainZone);

    expect(quantityInput()).toHaveValue("0");
    expect(screen.queryByText("2 included")).not.toBeInTheDocument();
    expect(
      screen.queryByText("kp.booking.service_line_total"),
    ).not.toBeInTheDocument();
  });

  it("shows the remaining stock and caps the quantity at it", async () => {
    availableServices = [
      { ...service, max_total_quantity: 10, remaining_total_quantity: 1 },
    ];
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await openServicesStep(user, includedZone);

    expect(screen.getByText("1 still available")).toBeInTheDocument();
    expect(await enterQuantity(user, "3")).toBe("3");
    expect(await enterQuantity(user, "4")).toBe("2");
  });
});
