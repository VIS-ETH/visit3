import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, screen } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import KpCompanyEvents from "../../pages/KpCompanyEvents";
import type {
  KpResponse,
  MyBookingResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testEvent,
  testRejectedBooking,
} from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const FIND_TIMEOUT = SLOW_WAIT;

const pastEvent: KpResponse = {
  ...testEvent,
  name: "Kontaktparty 2020",
  registration_open: "2020-01-01",
  registration_end: "2020-02-01",
  finalization_deadline: "2020-03-01",
  nametags_deadline: "2020-03-15",
  event_date: "2020-04-01",
};

const bookedClosedEvent: KpResponse = {
  ...testEvent,
  id: "event-closed",
  name: "Kontaktparty Booked",
  registration_open: "2000-01-01",
  registration_end: "2001-01-01",
  finalization_deadline: "2099-01-01",
  nametags_deadline: "2099-02-01",
  event_date: "2099-03-01",
};

let events: KpResponse[] = [];
let pastEventBooking: MyBookingResponse | null = null;
let bookingDelayMs = 0;

beforeEach(() => {
  events = [pastEvent];
  pastEventBooking = null;
  bookingDelayMs = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/kp/list`, () => HttpResponse.json(events)),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/my-booking`,
      async () => {
        if (bookingDelayMs) await delay(bookingDelayMs);
        return HttpResponse.json(pastEventBooking);
      },
    ),
  );
});

describe("the company event history", () => {
  it("lists a past event the company actually attended", async () => {
    pastEventBooking = { ...testBooking, can_register: false };

    renderWithProviders(<KpCompanyEvents />);

    expect(
      await screen.findByText(pastEvent.name, undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
  });

  it("hides a past event whose booking was rejected", async () => {
    pastEventBooking = testRejectedBooking;

    renderWithProviders(<KpCompanyEvents />);

    expect(
      await screen.findByText("kp.history.none", undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
    expect(screen.queryByText(pastEvent.name)).not.toBeInTheDocument();
  });
});

describe("the company event list", () => {
  it("keeps a booked event after its registration has closed", async () => {
    events = [bookedClosedEvent];
    pastEventBooking = { ...testBooking, can_register: false };

    renderWithProviders(<KpCompanyEvents />);

    expect(
      await screen.findByText(bookedClosedEvent.name, undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
  });

  it("keeps the list while the bookings reload", async () => {
    pastEventBooking = { ...testBooking, can_register: false };
    const { queryClient } = renderWithProviders(<KpCompanyEvents />);
    await screen.findByText(pastEvent.name, undefined, FIND_TIMEOUT);

    bookingDelayMs = 500;
    await act(async () => {
      void queryClient.invalidateQueries();
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    expect(screen.getByText(pastEvent.name)).toBeInTheDocument();
  });

  it("shows an error when a booking fails to load", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
        HttpResponse.json({ code: "error.internal" }, { status: 500 }),
      ),
    );

    renderWithProviders(<KpCompanyEvents />);

    expect(
      await screen.findByText("error.load_failed", undefined, FIND_TIMEOUT),
    ).toBeInTheDocument();
    expect(screen.queryByText("kp.history.none")).not.toBeInTheDocument();
  });
});
