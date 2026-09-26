import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEvent,
  testEventId,
  testTextRequirementId,
} from "../fixtures/kp-booking";
import { bookingRequirementElementId } from "../../utils/navigation";

const managePath = "/kp/:id/booking/:bookingId/manage/services";
const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;

beforeEach(() => {
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testEvent),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(testBooking),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
      () => HttpResponse.json(null),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/text`,
      () => HttpResponse.json({ text_value: "" }),
    ),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("a link to a missing requirement", () => {
  it("scrolls the services page to that requirement and focuses it", async () => {
    const scrollIntoView = vi.spyOn(Element.prototype, "scrollIntoView");
    const targetId = bookingRequirementElementId(testTextRequirementId);
    renderWithProviders(
      <Routes>
        <Route path={managePath} element={<KpBookingManage />} />
      </Routes>,
      { route: `${manageRoute}#${targetId}` },
    );

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledTimes(1));
    const target = document.getElementById(targetId);
    expect(scrollIntoView.mock.contexts[0]).toBe(target);
    expect(target?.contains(document.activeElement)).toBe(true);
  });
});
