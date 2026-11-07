import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingConfirmation from "../../pages/KpBookingConfirmation";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEventId,
  testOpenEvent,
} from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const pathname = `/kp/${testEventId}/booking/${testBookingId}`;

const renderConfirmation = (fromBookingProcess: boolean) =>
  renderWithProviders(
    <Routes>
      <Route
        path="/kp/:id/booking/:bookingId"
        element={<KpBookingConfirmation />}
      />
    </Routes>,
    {
      route: fromBookingProcess
        ? { pathname, state: { fromBookingProcess: true } }
        : pathname,
    },
  );

let slowBooking = false;

beforeEach(() => {
  slowBooking = false;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testOpenEvent),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/my-booking`,
      async () => {
        if (slowBooking) await delay(500);
        return HttpResponse.json(testBooking);
      },
    ),
  );
});

describe("the notice after a completed booking", () => {
  it("tells the company that VIS confirms the booking soon", async () => {
    const { user } = renderConfirmation(true);

    const dialog = await screen.findByRole("dialog", undefined, SLOW_WAIT);
    expect(
      screen.getByText("kp.booking.confirmation_just_booked_body"),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "common.ok" }));

    await waitFor(() => expect(dialog).not.toBeInTheDocument());
  });

  it("stays hidden when the booking is opened later", async () => {
    renderConfirmation(false);

    await screen.findByRole(
      "heading",
      { name: /kp\.booking\.summary_title/ },
      SLOW_WAIT,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("the booking summary", () => {
  it("keeps the summary while the booking reloads", async () => {
    const { queryClient } = renderConfirmation(false);
    await screen.findByRole(
      "heading",
      { name: /kp\.booking\.summary_title/ },
      SLOW_WAIT,
    );

    slowBooking = true;
    await act(async () => {
      void queryClient.invalidateQueries();
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    expect(
      screen.getByRole("heading", { name: /kp\.booking\.summary_title/ }),
    ).toBeInTheDocument();
  });
});
