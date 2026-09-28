import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
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

let pastEventBooking: MyBookingResponse | null = null;

beforeEach(() => {
  pastEventBooking = null;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/list`, () =>
      HttpResponse.json([pastEvent]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(pastEventBooking),
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
