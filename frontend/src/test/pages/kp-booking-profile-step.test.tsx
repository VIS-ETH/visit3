import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import KpBookingStepper from "../../pages/KpBookingStepper";
import { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import type {
  BookingResponse,
  BoothZoneWithAvailabilityResponse,
  KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  confirmProfileStep,
  continueToZoneButton,
  installCompanyProfileHandlers,
  profileConfirmCheckbox,
  testCompany,
  testCompanyProfile,
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
  booth_size: 4,
  base_price: 100000,
  included_services: [],
  is_full: false,
};

const registeredBooking: BookingResponse = {
  id: "booking-1",
  booking_number: 1,
  event_id: eventId,
  company_id: testCompany.id,
  booth_zone_id: zone.id,
  booth_nr: null,
  status: KpBookingStatus.REGISTERED,
  services: [],
  price: { net: 100000, vat: 8100, gross: 108100 },
};

const profileEditHref = `/company/profile?next=${encodeURIComponent(
  `/kp/${eventId}/booking`,
)}`;

const profileEditLink = () =>
  screen.getByRole("link", { name: "kp.booking.profile_edit" });

const registerUrl = `${testBackendUrl}/api/kp/events/${eventId}/bookings/register`;

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
      () => HttpResponse.json([]),
    ),
  );
  installCompanyProfileHandlers();
});

describe("booking wizard company profile step", () => {
  it("summarises the company profile of the booking company", async () => {
    renderWithProviders(<KpBookingStepper event={event} />);

    expect(await profileConfirmCheckbox()).toBeInTheDocument();
    expect(screen.getAllByText(testCompany.name).length).toBeGreaterThan(0);
    expect(
      screen.getByText(testCompanyProfile.brand_name!),
    ).toBeInTheDocument();
    expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
    expect(screen.getByText("ada@acme.test")).toBeInTheDocument();
    expect(screen.getByText("+41 79 000 00 00")).toBeInTheDocument();
    expect(
      screen.getByText(testCompanyProfile.general_email!),
    ).toBeInTheDocument();
    expect(
      screen.getByText(testCompanyProfile.general_phone!),
    ).toBeInTheDocument();
    expect(screen.getByText("Bahnhofstrasse 1")).toBeInTheDocument();
    expect(screen.getByText("8001 Zuerich")).toBeInTheDocument();
    expect(screen.getByText("Software")).toBeInTheDocument();
  });

  it("links to the company profile editor and back to the wizard", async () => {
    renderWithProviders(<KpBookingStepper event={event} />);

    await profileConfirmCheckbox();

    expect(profileEditLink()).toHaveAttribute("href", profileEditHref);
  });

  it("blocks the wizard until the profile is confirmed", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    const checkbox = await profileConfirmCheckbox();
    expect(continueToZoneButton()).toBeDisabled();

    await user.click(checkbox);

    expect(continueToZoneButton()).toBeEnabled();
  });

  it("lists the missing fields and keeps an incomplete profile unconfirmable", async () => {
    installCompanyProfileHandlers({
      company: {
        ...testCompany,
        profile_complete: false,
        profile_bookable: false,
        missing_profile_fields: ["kp_contact_user_id", "billing_city"],
      },
      profile: {
        ...testCompanyProfile,
        billing_city: "",
        kp_contact_user_id: null,
        kp_contact_user: null,
      },
    });
    renderWithProviders(<KpBookingStepper event={event} />);

    const checkbox = await profileConfirmCheckbox();

    expect(
      screen.getByText("kp.booking.profile_field.billing_city"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking.profile_field.kp_contact_user_id"),
    ).toBeInTheDocument();
    expect(profileEditLink()).toHaveAttribute("href", profileEditHref);
    expect(checkbox).toBeDisabled();
    expect(continueToZoneButton()).toBeDisabled();
  });

  it("lets a company book before it has written its description", async () => {
    installCompanyProfileHandlers({
      company: {
        ...testCompany,
        profile_complete: false,
        profile_bookable: true,
        missing_profile_fields: ["description"],
      },
      profile: { ...testCompanyProfile, description: "" },
    });
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    const checkbox = await profileConfirmCheckbox();

    expect(
      screen.getByText("kp.booking.profile_field.description"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking.profile_incomplete_deferred"),
    ).toBeInTheDocument();
    expect(checkbox).toBeEnabled();

    await user.click(checkbox);

    expect(continueToZoneButton()).toBeEnabled();
  });

  it("registers with the profile confirmation flag", async () => {
    let registered: unknown = null;
    server.use(
      http.post(registerUrl, async ({ request }) => {
        registered = await request.json();
        return HttpResponse.json(registeredBooking);
      }),
    );
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await confirmProfileStep(user);
    await user.click(
      screen.getByRole("button", { name: new RegExp(zone.name) }),
    );
    await user.click(
      screen.getByRole("button", { name: "kp.booking.continue_with_zone" }),
    );
    await screen.findByText("kp.booking.services_title", undefined, SLOW_WAIT);
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
        services: [],
      });
    }, SLOW_WAIT);
  });
});
