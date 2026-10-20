import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
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
import { continueToSummaryStep } from "../fixtures/booking-wizard";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const eventId = "event-1";

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

const zone: BoothZoneWithAvailabilityResponse = {
  id: "zone-1",
  event_id: eventId,
  name: "Main Hall",
  description: "",
  color: "#112233",
  order: 1,
  booth_size: 4,
  base_price: 100000,
  registration_open: true,
  is_full: false,
  included_services: [],
};

const serviceDefaults = {
  event_id: eventId,
  description: "",
  image_url: null,
  confirmation_description: null,
  max_quantity_per_booking: 1,
  max_total_quantity: 0,
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  remaining_total_quantity: null,
  is_active: true,
  requirements: [],
  included_services: [],
  excluded_service_ids: [],
};

const normalTable: ServiceResponse = {
  ...serviceDefaults,
  id: "normal",
  name: "Normal table",
  order: 1,
  price: 3000,
  excluded_service_ids: ["no-normal"],
};

const noNormalTable: ServiceResponse = {
  ...serviceDefaults,
  id: "no-normal",
  name: "No normal table",
  order: 2,
  price: 0,
  excluded_service_ids: ["normal"],
};

const standingTable: ServiceResponse = {
  ...serviceDefaults,
  id: "standing",
  name: "Standing table",
  order: 3,
  price: 4000,
  included_services: [{ service_id: "no-normal", included_quantity: 1 }],
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

const card = (name: string) =>
  within(screen.getByText(name).closest(".mantine-Paper-root") as HTMLElement);

const toggle = (name: string) => card(name).getByRole("switch");

const openServicesStep = async (user: UserEvent) => {
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
    "kp.booking.service_contains",
    "Contains {{contents}}",
  );
  i18n.addResource(
    "en",
    "common",
    "kp.booking.service_excluded_by",
    "Not combinable with {{name}}",
  );
});

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    http.get(csrfUrl, () => HttpResponse.json({ token: "csrf-1" })),
    http.get(myBookingUrl, () => HttpResponse.json(null)),
    http.get(zonesUrl, () => HttpResponse.json([zone])),
    http.get(servicesUrl, () =>
      HttpResponse.json([normalTable, noNormalTable, standingTable]),
    ),
  );
});

describe("service packages and exclusions in the booking wizard", () => {
  it("lists what a package contains", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await openServicesStep(user);

    expect(
      card("Standing table").getByText("Contains 1× No normal table"),
    ).toBeInTheDocument();
  });

  it("selects the contents of a package for free and drops them again", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await openServicesStep(user);
    await user.click(toggle("Standing table"));

    await waitFor(() => {
      expect(toggle("No normal table")).toBeChecked();
    });
    expect(card("No normal table").getByText("1 included")).toBeInTheDocument();

    await user.click(toggle("Standing table"));

    await waitFor(() => {
      expect(toggle("No normal table")).not.toBeChecked();
    });
  });

  it("blocks a service that a selected service excludes", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await openServicesStep(user);
    await user.click(toggle("Normal table"));

    expect(toggle("No normal table")).toBeDisabled();
    expect(toggle("Standing table")).toBeDisabled();
    expect(
      card("Standing table").getByText("Not combinable with Normal table"),
    ).toBeInTheDocument();
  });

  it("registers the package together with its contents", async () => {
    let registered: unknown = null;
    server.use(
      http.post(registerUrl, async ({ request }) => {
        registered = await request.json();
        return HttpResponse.json(registeredBooking);
      }),
    );
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await openServicesStep(user);
    await user.click(toggle("Standing table"));
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
        services: expect.arrayContaining([
          { service_id: "standing", quantity: 1 },
          { service_id: "no-normal", quantity: 1 },
        ]) as unknown,
      });
    }, SLOW_WAIT);
  });
});
