import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import KpBookingStepper from "../../pages/KpBookingStepper";
import type { KpResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import i18n from "../i18n";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { testMainZone, testSideZone, testVenueMap } from "../fixtures/venue";
import {
  confirmProfileStep,
  installCompanyProfileHandlers,
} from "../fixtures/company-profile";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

const openEvent: KpResponse = {
  id: testEventId,
  name: "Kontaktparty",
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

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const eventUrl = `${testBackendUrl}/api/kp/events/${testEventId}`;

const mapZoneButton = (name: string) =>
  screen.getByRole("button", { name, hidden: true });

const listZoneButton = () =>
  screen.getByRole("button", {
    name: new RegExp(`${testMainZone.booth_size} m²`),
  });

beforeAll(() => {
  i18n.addResource("en", "common", "kp.booth_size", "{{size}} m²");
});

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${eventUrl}/my-booking`, () => HttpResponse.json(null)),
    http.get(`${eventUrl}/venue`, () => HttpResponse.json(testVenueMap)),
    http.get(`${eventUrl}/booth-zones/available`, () =>
      HttpResponse.json([testMainZone, testSideZone]),
    ),
    http.get(`${eventUrl}/services/available`, () => HttpResponse.json([])),
  );
});

describe("the venue map inside the booking wizard", () => {
  it("selects the zone in the list when its shape is clicked on the map", async () => {
    const { user } = renderWithProviders(
      <KpBookingStepper event={openEvent} />,
    );

    await confirmProfileStep(user);
    await screen.findByRole("button", { name: testMainZone.name }, SLOW_WAIT);
    await user.click(mapZoneButton(testMainZone.name));

    expect(
      await screen.findByText(testMainZone.description, undefined, SLOW_WAIT),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "kp.booking.continue_with_zone" }),
    ).toBeEnabled();
  });

  it("marks the shape on the map when the zone is picked from the list", async () => {
    const { user } = renderWithProviders(
      <KpBookingStepper event={openEvent} />,
    );

    await confirmProfileStep(user);
    await screen.findByRole("button", { name: testMainZone.name }, SLOW_WAIT);
    await user.click(listZoneButton());

    expect(mapZoneButton(testMainZone.name)).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(mapZoneButton(testSideZone.name)).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });
});
