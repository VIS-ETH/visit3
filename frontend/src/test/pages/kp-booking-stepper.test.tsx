import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router";
import KpBookingStepper from "../../pages/KpBookingStepper";
import {
  KpBookingStatus,
  KpEventServiceRequirementType,
  KpServiceCategory,
} from "../../orval/generated/fastAPI.schemas";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  KpResponse,
  MyBookingResponse,
  ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
import { getGetMyBookingQueryKey } from "../../orval/generated/kp/kp";
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
import { notificationsShow } from "../notifications";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const eventId = "event-1";
const bookingRoute = `/kp/${eventId}/booking`;

const csrfUrl = `${testBackendUrl}/api/csrftoken`;
const myBookingUrl = `${testBackendUrl}/api/kp/events/${eventId}/my-booking`;
const zonesUrl = `${testBackendUrl}/api/kp/events/${eventId}/booth-zones/available`;
const servicesUrl = `${testBackendUrl}/api/kp/events/${eventId}/services/available`;
const registerUrl = `${testBackendUrl}/api/kp/events/${eventId}/bookings/register`;
const requirementTextUrl = `${testBackendUrl}/api/kp/booking-services/booking-service-1/requirements/requirement-1/text`;

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

const service: ServiceResponse = {
  id: "service-1",
  event_id: eventId,
  name: "Power Socket",
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  price: 5000,
  max_quantity_per_booking: 3,
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

const registeredBooking: BookingResponse = {
  id: "booking-1",
  booking_number: 1,
  event_id: eventId,
  company_id: "company-1",
  booth_zone_id: zone.id,
  booth_nr: null,
  status: KpBookingStatus.REGISTERED,
  services: [
    {
      id: "booking-service-1",
      booking_id: "booking-1",
      service_id: service.id,
      quantity: 1,
      included_quantity: 0,
      charged_quantity: 1,
      unit_price: service.price,
      line_net: service.price,
      service,
    },
  ],
  price: { net: 0, vat: 0, gross: 0 },
};

const existingBooking: BookingResponse = {
  ...registeredBooking,
  id: "booking-existing",
  booking_number: 7,
};

const rejectedExistingBooking: MyBookingResponse = {
  ...existingBooking,
  status: KpBookingStatus.REJECTED,
  can_register: true,
};

const alreadyExists = () =>
  HttpResponse.json(
    { code: "error.kp_booking_already_exists", statusCode: 409 },
    { status: 409 },
  );

let registerRequests = 0;
let requirementTextRequests = 0;
let myBookingResponse: BookingResponse | null = null;

const LocationProbe = () => {
  const location = useLocation();
  return <span data-testid="location">{location.pathname}</span>;
};

const renderStepper = () =>
  renderWithProviders(
    <>
      <LocationProbe />
      <Routes>
        <Route
          path="/kp/:id/booking"
          element={<KpBookingStepper event={event} />}
        />
      </Routes>
    </>,
    { route: bookingRoute },
  );

const currentPath = () => screen.getByTestId("location").textContent;

const selectZoneAndContinue = async (user: UserEvent) => {
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

const registerButton = () =>
  screen.getByRole("button", { name: "kp.booking.summary_confirm_register" });

const fillServiceRequirement = async (user: UserEvent) => {
  const quantity = screen.getByLabelText("kp.booking.service_quantity");
  await user.clear(quantity);
  await user.type(quantity, "1");
  await user.type(
    await screen.findByLabelText(
      service.requirements[0].name,
      undefined,
      SLOW_WAIT,
    ),
    "Hello booth",
  );
};

beforeEach(() => {
  registerRequests = 0;
  requirementTextRequests = 0;
  myBookingResponse = null;
  notificationsShow.mockClear();
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    emptyVenueHandler,
    http.get(csrfUrl, () => HttpResponse.json({ token: "csrf-1" })),
    http.get(myBookingUrl, () => HttpResponse.json(myBookingResponse)),
    http.get(zonesUrl, () => HttpResponse.json([zone])),
    http.get(servicesUrl, () => HttpResponse.json([service])),
  );
});

describe("booking registration", () => {
  it("stays on the wizard and re-enables the button when register fails", async () => {
    server.use(
      http.post(registerUrl, () => {
        registerRequests += 1;
        return HttpResponse.json(
          { code: "error.internal", statusCode: 500 },
          { status: 500 },
        );
      }),
    );
    const { user } = renderStepper();

    await selectZoneAndContinue(user);
    await continueToSummaryStep(user);
    await acceptConsents(user);
    await user.click(registerButton());

    await waitFor(() => {
      expect(registerRequests).toBe(1);
    }, SLOW_WAIT);
    await waitFor(() => {
      expect(registerButton()).toBeEnabled();
    }, SLOW_WAIT);
    expect(currentPath()).toBe(bookingRoute);
    expect(screen.getByText("kp.booking.summary_title")).toBeInTheDocument();
  });

  it("opens the existing booking and seeds its cache when one already exists", async () => {
    server.use(
      http.post(registerUrl, () => {
        registerRequests += 1;
        myBookingResponse = existingBooking;
        return alreadyExists();
      }),
    );
    const { user, queryClient } = renderStepper();

    await selectZoneAndContinue(user);
    await continueToSummaryStep(user);
    await acceptConsents(user);
    await user.click(registerButton());

    await waitFor(() => {
      expect(currentPath()).toBe(`${bookingRoute}/${existingBooking.id}`);
    }, SLOW_WAIT);
    expect(registerRequests).toBe(1);
    expect(queryClient.getQueryData(getGetMyBookingQueryKey(eventId))).toEqual(
      existingBooking,
    );
  });

  it("stays on the wizard when the existing booking is rejected", async () => {
    server.use(
      http.post(registerUrl, () => {
        registerRequests += 1;
        myBookingResponse = rejectedExistingBooking;
        return alreadyExists();
      }),
    );
    const { user, queryClient } = renderStepper();

    await selectZoneAndContinue(user);
    await continueToSummaryStep(user);
    await acceptConsents(user);
    await user.click(registerButton());

    await waitFor(() => {
      expect(
        queryClient.getQueryData(getGetMyBookingQueryKey(eventId)),
      ).toEqual(rejectedExistingBooking);
    }, SLOW_WAIT);
    expect(registerRequests).toBe(1);
    expect(currentPath()).toBe(bookingRoute);
  });

  it("warns and opens the services tab when a requirement upload fails", async () => {
    server.use(
      http.post(registerUrl, () => {
        registerRequests += 1;
        return HttpResponse.json(registeredBooking);
      }),
      http.put(requirementTextUrl, () => {
        requirementTextRequests += 1;
        return HttpResponse.json(
          { code: "error.internal", statusCode: 500 },
          { status: 500 },
        );
      }),
    );
    const { user } = renderStepper();

    await selectZoneAndContinue(user);
    await fillServiceRequirement(user);
    await continueToSummaryStep(user);
    await acceptConsents(user);
    await user.click(registerButton());

    await waitFor(() => {
      expect(currentPath()).toBe(
        `${bookingRoute}/${registeredBooking.id}/manage/services`,
      );
    }, SLOW_WAIT);
    expect(registerRequests).toBe(1);
    expect(requirementTextRequests).toBe(1);
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({
        color: "yellow",
        title: "kp.booking.register_requirements_failed_title",
        message: "kp.booking.register_requirements_failed_message",
      }),
    );
  });

  it("opens the new booking when registration succeeds", async () => {
    server.use(
      http.post(registerUrl, async ({ request }) => {
        registerRequests += 1;
        expect(await request.json()).toEqual({
          booth_zone_id: zone.id,
          confirm_profile: true,
          services: [],
        });
        return HttpResponse.json(registeredBooking);
      }),
    );
    const { user } = renderStepper();

    await selectZoneAndContinue(user);
    await continueToSummaryStep(user);
    await acceptConsents(user);
    await user.click(registerButton());

    await waitFor(() => {
      expect(currentPath()).toBe(`${bookingRoute}/${registeredBooking.id}`);
    }, SLOW_WAIT);
    expect(registerRequests).toBe(1);
  });

  it("registers once when the confirm button is double clicked", async () => {
    server.use(
      http.post(registerUrl, async () => {
        registerRequests += 1;
        await delay(50);
        return HttpResponse.json(registeredBooking);
      }),
    );
    const { user } = renderStepper();

    await selectZoneAndContinue(user);
    await continueToSummaryStep(user);
    await acceptConsents(user);
    const button = registerButton();
    await user.dblClick(button);

    expect(registerRequests).toBe(1);
    expect(button).toBeDisabled();
    await waitFor(() => {
      expect(currentPath()).toBe(`${bookingRoute}/${registeredBooking.id}`);
    }, SLOW_WAIT);
    expect(registerRequests).toBe(1);
  });
});

describe("booking summary", () => {
  it("blocks registration until both consents are accepted", async () => {
    server.use(
      http.post(registerUrl, () => {
        registerRequests += 1;
        return HttpResponse.json(registeredBooking);
      }),
    );
    const { user } = renderStepper();

    await selectZoneAndContinue(user);
    await continueToSummaryStep(user);
    await user.click(registerButton());

    expect(registerRequests).toBe(0);
    expect(currentPath()).toBe(bookingRoute);
  });

  it("lists the selected service and the resulting total", async () => {
    const { user } = renderStepper();

    await selectZoneAndContinue(user);
    await fillServiceRequirement(user);
    await continueToSummaryStep(user);

    expect(screen.getByText(service.name)).toBeInTheDocument();
    expect(screen.getByText("CHF 1050.00")).toBeInTheDocument();
  });
});
