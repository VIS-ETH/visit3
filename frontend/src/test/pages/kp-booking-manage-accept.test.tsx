import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import { KpEventServiceRequirementType } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEvent,
  testEventId,
  testServiceId,
} from "../fixtures/kp-booking";

const requirementTypes = [
  KpEventServiceRequirementType.image,
  KpEventServiceRequirementType.pdf,
  KpEventServiceRequirementType.video,
  KpEventServiceRequirementType.file,
];

const bookedService = testBooking.services![0];

const bookingWithEveryUploadType = {
  ...testBooking,
  services: [
    {
      ...bookedService,
      service: {
        ...bookedService.service,
        requirements: requirementTypes.map((type, index) => ({
          id: `requirement-${index}`,
          service_id: testServiceId,
          type,
          name: `Requirement ${index}`,
          description: `Upload for ${type}`,
          order: index,
        })),
      },
    },
  ],
};

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
      HttpResponse.json(bookingWithEveryUploadType),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
      () => HttpResponse.json(null),
    ),
  );
});

describe("KpBookingManage upload restrictions", () => {
  it("only accepts the formats the backend stores", async () => {
    const { container } = renderWithProviders(
      <Routes>
        <Route path={managePath} element={<KpBookingManage />} />
      </Routes>,
      { route: manageRoute },
    );

    await screen.findByText(
      "kp.booking_manage.allowed_formats_image",
      {},
      { timeout: 5000 },
    );

    const accepts = [...container.querySelectorAll('input[type="file"]')].map(
      (input) => input.getAttribute("accept"),
    );

    expect(accepts).toEqual([
      "image/png,image/jpeg,image/gif,image/webp",
      "application/pdf",
      "video/mp4,video/quicktime,video/webm",
      null,
    ]);
    expect(
      screen.getByText("kp.booking_manage.allowed_formats_pdf"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking_manage.allowed_formats_video"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("kp.booking_manage.allowed_formats_file"),
    ).toBeInTheDocument();
  });
});
