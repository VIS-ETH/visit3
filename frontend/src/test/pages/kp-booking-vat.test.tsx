import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingConfirmation from "../../pages/KpBookingConfirmation";
import KpBookingManageOverview from "../../pages/KpBookingManageOverview";
import KpBookingStepper from "../../pages/KpBookingStepper";
import KpCompanyView from "../../pages/KpCompanyView";
import { KpBookingRecap } from "../../components/KpBookingRecap";
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
  requirements: [],
};

const booking: BookingResponse = {
  id: "booking-1",
  booking_number: 1,
  event_id: eventId,
  company_id: "company-1",
  booth_zone_id: zone.id,
  booth_nr: null,
  status: KpBookingStatus.REGISTERED,
  booth_zone: { ...zone, included_services: [] },
  services: [],
  additional_service_charges: [],
  net_total: 105000,
  price: { net: 105000, vat: 8505, gross: 113505 },
};

const openSummary = async (user: UserEvent) => {
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
    http.get(`${testBackendUrl}/api/kp/events/${eventId}`, () =>
      HttpResponse.json(event),
    ),
    http.get(`${testBackendUrl}/api/kp/events/${eventId}/my-booking`, () =>
      HttpResponse.json(booking),
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
  installCompanyProfileHandlers();
});

describe("vat in the booking wizard", () => {
  it("explains that the listed prices exclude vat", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/${eventId}/my-booking`, () =>
        HttpResponse.json(null),
      ),
    );
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openSummary(user);

    expect(
      screen.getAllByLabelText("kp.booking.price_excl_vat_hint"),
    ).toHaveLength(1);
  });

  it("breaks the summary total into net, vat and gross", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/${eventId}/my-booking`, () =>
        HttpResponse.json(null),
      ),
    );
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openSummary(user);
    const quantity = screen.getByLabelText("kp.booking.service_quantity");
    await user.clear(quantity);
    await user.type(quantity, "1");
    await continueToSummaryStep(user);

    expect(screen.getByText("kp.booking.summary_net")).toBeInTheDocument();
    expect(screen.getByText("kp.booking.summary_vat_rate")).toBeInTheDocument();
    expect(screen.getByText("kp.booking.summary_gross")).toBeInTheDocument();
    expect(screen.getByText("CHF 1050.00")).toBeInTheDocument();
    expect(screen.getByText("CHF 85.05")).toBeInTheDocument();
    expect(screen.getByText("CHF 1135.05")).toBeInTheDocument();
  });
});

describe("vat on the booking recap", () => {
  it("renders the price breakdown the backend computed", () => {
    renderWithProviders(
      <KpBookingRecap booking={booking} vatRatePercent={8.1} />,
    );

    expect(screen.getByText("CHF 1050.00")).toBeInTheDocument();
    expect(screen.getByText("CHF 85.05")).toBeInTheDocument();
    expect(screen.getByText("CHF 1135.05")).toBeInTheDocument();
  });
});

describe("vat on the company event view", () => {
  it("shows the gross booking total instead of the zone base price", async () => {
    renderWithProviders(
      <Routes>
        <Route path="/kp/:id" element={<KpCompanyView />} />
      </Routes>,
      { route: `/kp/${eventId}` },
    );

    expect(
      await screen.findByText(
        "kp.company_view.booking_total_gross",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("common.currency 1135.05")).toBeInTheDocument();
  });
});

describe("vat on the booking pages that recap a stored booking", () => {
  it("shows the rate on the confirmation page", async () => {
    renderWithProviders(
      <Routes>
        <Route
          path="/kp/:id/booking/:bookingId"
          element={<KpBookingConfirmation />}
        />
      </Routes>,
      { route: `/kp/${eventId}/booking/${booking.id}` },
    );

    expect(
      await screen.findByText(
        "kp.booking.summary_vat_rate",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
  });

  it("shows the rate on the manage overview page", async () => {
    renderWithProviders(
      <Routes>
        <Route
          path="/kp/:id/booking/:bookingId/manage"
          element={<KpBookingManageOverview />}
        />
      </Routes>,
      { route: `/kp/${eventId}/booking/${booking.id}/manage` },
    );

    expect(
      await screen.findByText(
        "kp.booking.summary_vat_rate",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
  });
});
