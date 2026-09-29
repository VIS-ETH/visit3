import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import BookingsOverview from "../../pages/BookingsOverview";
import {
  KpBookingStatus,
  type BookingSummaryResponse,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import i18n from "../i18n";
import { renderWithProviders } from "../render";
import { testEvent } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const latestEvent: KpResponse = {
  ...testEvent,
  id: "22222222-2222-2222-2222-222222222222",
  name: "KP 2026",
};

const olderEvent: KpResponse = {
  ...testEvent,
  id: "11111111-1111-1111-1111-111111111111",
  name: "KP 2025",
};

const totals = (count: number, base: number, services: number) => {
  const net = base + services;
  const vat = Math.round(net * 0.081);
  return { count, base, services, price: { net, vat, gross: net + vat } };
};

const summaryFor = (
  eventId: string,
  scale: number,
): BookingSummaryResponse => ({
  event_id: eventId,
  vat_rate_percent: 8.1,
  total: totals(3 * scale, 400000 * scale, 50000 * scale),
  by_status: [
    {
      status: KpBookingStatus.REGISTERED,
      ...totals(2 * scale, 300000 * scale, 50000 * scale),
    },
    {
      status: KpBookingStatus.CONFIRMED,
      ...totals(scale, 100000 * scale, 0),
    },
  ],
  by_zone: [
    {
      booth_zone_id: "zone-main",
      name: "Main hall",
      color: "#112233",
      base_price: 150000,
      capacity: 20,
      free: 20 - 2 * scale,
      ...totals(2 * scale, 300000 * scale, 50000 * scale),
    },
    {
      booth_zone_id: "zone-closed",
      name: "Closed hall",
      color: "#445566",
      base_price: 100000,
      capacity: 0,
      free: 0,
      ...totals(scale, 100000 * scale, 0),
    },
  ],
  capacity: 20,
  free: 20 - 2 * scale,
  cancelled_count: 1,
  rejected_count: 0,
});

let summaryRequests: string[] = [];

beforeEach(() => {
  summaryRequests = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/list`, () =>
      HttpResponse.json([latestEvent, olderEvent]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/bookings/summary`,
      ({ params }) => {
        const eventId = String(params.eventId);
        summaryRequests.push(eventId);
        return HttpResponse.json(
          summaryFor(eventId, eventId === latestEvent.id ? 1 : 2),
        );
      },
    ),
  );
});

describe("the bookings overview", () => {
  it("shows the gross total of the latest event with its breakdown", async () => {
    renderWithProviders(<BookingsOverview />);

    expect(
      await screen.findByText("CHF 4864.50", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(summaryRequests).toEqual([latestEvent.id]);
    expect(
      screen.getByText("kp.booking.status.registered.label"),
    ).toBeInTheDocument();
    expect(screen.getByText("Main hall")).toBeInTheDocument();
    expect(screen.getAllByText("4000.00").length).toBeGreaterThan(0);
  });

  it("loads the summary of another event when it is picked", async () => {
    const { user } = renderWithProviders(<BookingsOverview />);
    await screen.findByText("CHF 4864.50", undefined, SLOW_WAIT);

    await user.click(
      screen.getByRole("combobox", { name: "kp.bookings_overview.event" }),
    );
    await user.click(await screen.findByRole("option", { name: "KP 2025" }));

    expect(
      await screen.findByText("CHF 9729.00", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(summaryRequests).toEqual([latestEvent.id, olderEvent.id]),
    );
  });

  it("shows the price and the occupancy of every zone", async () => {
    i18n.addResource(
      "en",
      "common",
      "kp.bookings_overview.per_booth",
      "CHF {{price}} per booth",
    );
    renderWithProviders(<BookingsOverview />);
    await screen.findByText("CHF 4864.50", undefined, SLOW_WAIT);

    const mainHall = screen.getByRole("row", { name: /Main hall/ });
    expect(
      within(mainHall).getByText("CHF 1500.00 per booth"),
    ).toBeInTheDocument();
    expect(within(mainHall).getByText("2 / 20")).toBeInTheDocument();
    expect(within(mainHall).getByText("18")).toBeInTheDocument();
    const closedHall = screen.getByRole("row", { name: /Closed hall/ });
    expect(within(closedHall).getByText("1 / 0")).toBeInTheDocument();
    expect(within(closedHall).getByText("0")).toBeInTheDocument();
    const totalRow = screen.getByRole("row", {
      name: /kp.bookings_overview.all/,
    });
    expect(within(totalRow).getByText("3 / 20")).toBeInTheDocument();
    expect(within(totalRow).getByText("18")).toBeInTheDocument();
  });
});
