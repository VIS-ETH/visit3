import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import KpBookingStepper from "../../pages/KpBookingStepper";
import type {
  BoothZoneWithAvailabilityResponse,
  KpResponse,
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
const termsUrl = "https://vis.ethz.ch/kp/agb";

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
  await continueToSummaryStep(user);
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
      () => HttpResponse.json([]),
    ),
  );
  installCompanyProfileHandlers();
});

describe("terms of service consent", () => {
  it("links the configured terms document in a new tab", async () => {
    const { user } = renderWithProviders(
      <KpBookingStepper event={{ ...event, terms_url: termsUrl }} />,
    );

    await openSummary(user);

    const link = screen.getByRole("link", {
      name: "kp.booking.confirm_agb_link",
    });
    expect(link).toHaveAttribute("href", termsUrl);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(
      screen.getByText("kp.booking.confirm_agb_prefix"),
    ).toBeInTheDocument();
  });

  it("falls back to plain consent text without a terms document", async () => {
    const { user } = renderWithProviders(<KpBookingStepper event={event} />);

    await openSummary(user);

    expect(
      screen.queryByRole("link", { name: "kp.booking.confirm_agb_link" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("kp.booking.confirm_agb_checkbox"),
    ).toBeInTheDocument();
  });
});
