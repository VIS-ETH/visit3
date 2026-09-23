import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import KpBookingStepper from "../../pages/KpBookingStepper";
import {
  KpEventServiceRequirementType,
  KpServiceCategory,
} from "../../orval/generated/fastAPI.schemas";
import type {
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
import { emptyVenueHandler } from "../fixtures/venue";

const eventId = "event-1";

const csrfUrl = `${testBackendUrl}/api/csrftoken`;
const myBookingUrl = `${testBackendUrl}/api/kp/events/${eventId}/my-booking`;
const zonesUrl = `${testBackendUrl}/api/kp/events/${eventId}/booth-zones/available`;
const servicesUrl = `${testBackendUrl}/api/kp/events/${eventId}/services/available`;

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

const maxQuantity = 3;
const unitPriceCents = 2500;

const service: ServiceResponse = {
  id: "service-1",
  event_id: eventId,
  name: "Power Socket",
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  price: unitPriceCents,
  max_quantity_per_booking: maxQuantity,
  max_total_quantity: 0,
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  is_active: true,
  requirements: [
    {
      id: "requirement-1",
      service_id: "service-1",
      type: KpEventServiceRequirementType.text,
      name: "Slogan",
      description: "",
      order: 1,
    },
  ],
};

const boothElement: ServiceResponse = {
  ...service,
  id: "service-2",
  name: "Extra Table",
  category: KpServiceCategory.BOOTH_ELEMENT,
  requirements: [],
};

const quantityInput = () =>
  screen.getByLabelText<HTMLInputElement>("kp.booking.service_quantity");

const openServicesStep = async (user: UserEvent) => {
  await confirmProfileStep(user);
  await user.click(
    await screen.findByRole(
      "button",
      { name: new RegExp(zone.name) },
      { timeout: 5000 },
    ),
  );
  await user.click(
    screen.getByRole("button", { name: "kp.booking.continue_with_zone" }),
  );
  await screen.findByText("kp.booking.services_title");
};

const enterQuantity = async (user: UserEvent, typed: string) => {
  await user.clear(quantityInput());
  await user.type(quantityInput(), typed);
  return Number(quantityInput().value);
};

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    emptyVenueHandler,
    http.get(csrfUrl, () => HttpResponse.json({ token: "csrf-1" })),
    http.get(myBookingUrl, () => HttpResponse.json(null)),
    http.get(zonesUrl, () => HttpResponse.json([zone])),
    http.get(servicesUrl, () => HttpResponse.json([service])),
  );
});

describe("the available services query", () => {
  it("asks for every category once and filters them in the browser", async () => {
    const requestedUrls: string[] = [];
    server.use(
      http.get(servicesUrl, ({ request }) => {
        requestedUrls.push(request.url);
        return HttpResponse.json([service, boothElement]);
      }),
    );
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);

    expect(screen.getByText(service.name)).toBeInTheDocument();
    expect(screen.queryByText(boothElement.name)).not.toBeInTheDocument();
    expect(requestedUrls.length).toBeGreaterThan(0);
    for (const url of requestedUrls) {
      expect(new URL(url).search).toBe("");
    }
  });
});

describe("service quantity input", () => {
  it("shows the per booking cap hint", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);

    expect(
      screen.getByText("kp.booking.service_max_per_booking"),
    ).toBeInTheDocument();
    expect(quantityInput()).toHaveValue("0");
    expect(
      screen.queryByText("kp.booking.service_line_total"),
    ).not.toBeInTheDocument();
  });

  it.each(["999", "-1", "2.5"])(
    "clamps %s to a whole number within the allowed range",
    async (typed) => {
      const { user } = renderWithProviders(<KpBookingStepper event={event} />);

      await openServicesStep(user);
      const quantity = await enterQuantity(user, typed);

      expect(Number.isInteger(quantity)).toBe(true);
      expect(quantity).toBeGreaterThanOrEqual(0);
      expect(quantity).toBeLessThanOrEqual(maxQuantity);
    },
  );

  it("refuses digits that would exceed the per booking maximum", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);

    expect(await enterQuantity(user, "999")).toBe(0);
    expect(await enterQuantity(user, String(maxQuantity))).toBe(maxQuantity);
    expect(await enterQuantity(user, String(maxQuantity + 1))).toBe(0);
  });

  it("drops the minus sign of a negative quantity", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);

    expect(await enterQuantity(user, "-1")).toBe(1);
  });

  it("ignores the decimal separator of a fractional quantity", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);

    expect(await enterQuantity(user, "2.5")).toBe(2);
  });

  it("renders the line total for the entered quantity", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openServicesStep(user);
    const quantity = await enterQuantity(user, "2");

    expect(
      screen.getByText("kp.booking.service_line_total"),
    ).toBeInTheDocument();
    expect(screen.getByText("CHF 50.00")).toBeInTheDocument();
    expect(quantity * unitPriceCents).toBe(5000);
  });
});
