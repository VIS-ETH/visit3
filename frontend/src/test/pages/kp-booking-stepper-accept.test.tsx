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
  is_full: false,
};

const uploadTypes = [
  KpEventServiceRequirementType.image,
  KpEventServiceRequirementType.pdf,
  KpEventServiceRequirementType.video,
  KpEventServiceRequirementType.file,
];

const service: ServiceResponse = {
  id: "service-1",
  event_id: eventId,
  name: "Power Socket",
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  price: 2500,
  max_quantity_per_booking: 3,
  max_total_quantity: 0,
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  is_active: true,
  requirements: uploadTypes.map((type, index) => ({
    id: `requirement-${index}`,
    service_id: "service-1",
    type,
    name: `Requirement ${index}`,
    description: "",
    order: index,
  })),
};

const openRequirements = async (user: UserEvent) => {
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
  const quantity = screen.getByLabelText<HTMLInputElement>(
    "kp.booking.service_quantity",
  );
  await user.clear(quantity);
  await user.type(quantity, "1");
  await screen.findByText("kp.booking.service_requirements");
};

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    emptyVenueHandler,
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
      () => HttpResponse.json([service]),
    ),
  );
});

describe("booking wizard upload restrictions", () => {
  it("accepts the formats the backend stores and leaves plain files open", async () => {
    const { container, user } = renderWithProviders(
      <KpBookingStepper event={event} />,
    );

    await openRequirements(user);

    const accepts = [...container.querySelectorAll('input[type="file"]')].map(
      (input) => input.getAttribute("accept"),
    );

    expect(accepts).toEqual([
      "image/png,image/jpeg,image/gif,image/webp",
      "application/pdf",
      "video/mp4,video/quicktime,video/webm",
      null,
    ]);
  });

  it("shows the allowed formats hint of each requirement", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openRequirements(user);

    expect(
      screen.getByText("kp.booking_manage.allowed_formats_image"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking_manage.allowed_formats_pdf"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking_manage.allowed_formats_video"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking_manage.allowed_formats_file"),
    ).toBeInTheDocument();
  });
});
