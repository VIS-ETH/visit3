import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import KpBookingStepper from "../../pages/KpBookingStepper";
import type { KpResponse } from "../../orval/generated/fastAPI.schemas";
import mainHall from "../../assets/venue/main-hall.webp";
import redHall from "../../assets/venue/red-hall.webp";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import i18n from "../i18n";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { testMainZone, testSideZone } from "../fixtures/venue";
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

let venueRequests = 0;

beforeAll(() => {
  i18n.addResource("en", "common", "kp.booth_size", "{{size}} m²");
});

beforeEach(() => {
  venueRequests = 0;
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${eventUrl}/my-booking`, () => HttpResponse.json(null)),
    http.get(`${eventUrl}/venue`, () => {
      venueRequests += 1;
      return HttpResponse.json(null, { status: 500 });
    }),
    http.get(`${eventUrl}/booth-zones/available`, () =>
      HttpResponse.json([testMainZone, testSideZone]),
    ),
    http.get(`${eventUrl}/services/available`, () => HttpResponse.json([])),
  );
});

describe("the floor plans inside the booking wizard", () => {
  it("shows both hall plans as plain images without loading a venue map", async () => {
    const { user } = renderWithProviders(
      <KpBookingStepper event={openEvent} />,
    );

    await confirmProfileStep(user);

    expect(
      screen.getByRole("img", { name: "kp.venue.floor_plan_main_hall_alt" }),
    ).toHaveAttribute("src", mainHall);
    expect(
      screen.getByRole("img", { name: "kp.venue.floor_plan_red_hall_alt" }),
    ).toHaveAttribute("src", redHall);
    expect(
      screen.queryByRole("group", { name: "kp.venue.map_label" }),
    ).not.toBeInTheDocument();
    expect(venueRequests).toBe(0);
  });

  it("picks a zone from the list without any venue layout", async () => {
    const { user } = renderWithProviders(
      <KpBookingStepper event={openEvent} />,
    );

    await confirmProfileStep(user);
    await user.click(
      await screen.findByRole(
        "button",
        { name: new RegExp(`${testMainZone.booth_size} m²`) },
        SLOW_WAIT,
      ),
    );

    expect(
      await screen.findByText(testMainZone.description, undefined, SLOW_WAIT),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: "kp.booking.continue_with_zone" }),
    ).toBeEnabled();
    expect(venueRequests).toBe(0);
  });
});
