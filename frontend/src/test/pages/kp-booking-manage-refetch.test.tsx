import { act } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import { getGetMyBookingQueryKey } from "../../orval/generated/kp/kp";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEvent,
  testEventId,
} from "../fixtures/kp-booking";

const managePath = "/kp/:id/booking/:bookingId/manage/services";
const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;

let bookingRequests = 0;
let releasePendingBooking: () => void;
let pendingBooking: Promise<void>;

beforeEach(() => {
  bookingRequests = 0;
  pendingBooking = new Promise<void>((resolve) => {
    releasePendingBooking = resolve;
  });
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testEvent),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/my-booking`,
      async () => {
        bookingRequests += 1;
        if (bookingRequests > 1) await pendingBooking;
        return HttpResponse.json(testBooking);
      },
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/text`,
      () => HttpResponse.json({ text_value: "" }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
      () => HttpResponse.json(null),
    ),
  );
});

describe("KpBookingManage background refetch", () => {
  it("keeps typed requirement text while the booking refetches", async () => {
    const { user, queryClient } = renderWithProviders(
      <Routes>
        <Route path={managePath} element={<KpBookingManage />} />
      </Routes>,
      { route: manageRoute },
    );

    const textarea = await screen.findByPlaceholderText(
      "kp.booking_manage.text_placeholder",
      {},
      { timeout: 5000 },
    );
    await user.type(textarea, "Our slogan");
    expect(textarea).toHaveValue("Our slogan");

    await act(async () => {
      void queryClient.invalidateQueries({
        queryKey: getGetMyBookingQueryKey(testEventId),
      });
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(bookingRequests).toBe(2);
    });
    expect(
      screen.getByPlaceholderText("kp.booking_manage.text_placeholder"),
    ).toHaveValue("Our slogan");

    releasePendingBooking();

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("kp.booking_manage.text_placeholder"),
      ).toHaveValue("Our slogan");
    });
  });
});
