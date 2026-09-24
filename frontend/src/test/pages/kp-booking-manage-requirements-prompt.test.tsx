import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import {
  KpBookingStatus,
  KpEventServiceRequirementType,
  KpServiceCategory,
  type BookingResponse,
  type ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
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
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const managePath = "/kp/:id/booking/:bookingId/manage/services";
const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;
const addedBookingServiceId = "99999999-0000-0000-0000-000000000001";
const logoRequirementId = "99999999-0000-0000-0000-000000000002";
const logoTextUrl = `${testBackendUrl}/api/kp/booking-services/${addedBookingServiceId}/requirements/${logoRequirementId}/text`;

const bannerService: ServiceResponse = {
  id: "99999999-0000-0000-0000-000000000003",
  event_id: testEventId,
  name: "Banner",
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 2,
  price: 2000,
  max_quantity_per_booking: 1,
  max_total_quantity: 0,
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  is_active: true,
  requirements: [
    {
      id: logoRequirementId,
      service_id: "99999999-0000-0000-0000-000000000003",
      type: KpEventServiceRequirementType.text,
      name: "Banner text",
      description: "What the banner says",
      order: 1,
    },
  ],
};

const bookingWithBanner = (booking: BookingResponse): BookingResponse => ({
  ...booking,
  services: [
    ...(booking.services ?? []),
    {
      id: addedBookingServiceId,
      booking_id: testBookingId,
      service_id: bannerService.id,
      quantity: 1,
      included_quantity: 0,
      charged_quantity: 1,
      unit_price: bannerService.price,
      line_net: bannerService.price,
      service: bannerService,
    },
  ],
});

let savedTexts: unknown[] = [];

const serveBooking = (booking: BookingResponse) => {
  let current = booking;
  server.use(
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(current),
    ),
    http.post(
      `${testBackendUrl}/api/kp/bookings/${testBookingId}/services`,
      () => {
        current = bookingWithBanner(booking);
        return HttpResponse.json(current);
      },
    ),
  );
};

const renderManage = () =>
  renderWithProviders(
    <Routes>
      <Route path={managePath} element={<KpBookingManage />} />
    </Routes>,
    { route: manageRoute },
  );

const addBanner = async (user: UserEvent) => {
  const card = (
    await screen.findByText(bannerService.name, undefined, SLOW_WAIT)
  ).closest(".mantine-Paper-root") as HTMLElement;
  await user.click(within(card).getByRole("switch"));
  await user.click(
    screen.getByRole("button", {
      name: "kp.booking_manage.add_services_submit",
    }),
  );
  await user.click(
    await screen.findByRole(
      "button",
      { name: "kp.booking_manage.confirm_add_services_submit" },
      SLOW_WAIT,
    ),
  );
  return screen.findByRole(
    "dialog",
    { name: "kp.booking_manage.requirements_prompt_title" },
    SLOW_WAIT,
  );
};

beforeEach(() => {
  savedTexts = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testEvent),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([bannerService]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
      () => HttpResponse.json(null),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/text`,
      () => HttpResponse.json(null),
    ),
    http.put(logoTextUrl, async ({ request }) => {
      savedTexts.push(await request.json());
      return HttpResponse.json({
        id: "answer-1",
        booking_service_id: addedBookingServiceId,
        requirement_id: logoRequirementId,
        text_value: "Hello",
      });
    }),
  );
});

describe("the requirements prompt after adding services", () => {
  it.each([KpBookingStatus.REGISTERED, KpBookingStatus.CONFIRMED])(
    "asks for the requirements of the added service of a %s booking",
    async (status) => {
      serveBooking({ ...testBooking, status });
      const { user } = renderManage();

      const dialog = await addBanner(user);
      await user.type(
        within(dialog).getByPlaceholderText(
          "kp.booking_manage.text_placeholder",
        ),
        "Hello",
      );
      await user.click(
        within(dialog).getByRole("button", {
          name: "kp.booking_manage.requirements_prompt_save",
        }),
      );

      await waitFor(() => {
        expect(savedTexts).toEqual([{ text_value: "Hello" }]);
      }, SLOW_WAIT);
      await waitFor(() => expect(dialog).not.toBeInTheDocument(), SLOW_WAIT);
    },
  );

  it("lets the company fill the requirements in later", async () => {
    serveBooking(testBooking);
    const { user } = renderManage();

    const dialog = await addBanner(user);
    await user.click(
      within(dialog).getByRole("button", {
        name: "kp.booking_manage.requirements_prompt_later",
      }),
    );

    await waitFor(() => expect(dialog).not.toBeInTheDocument(), SLOW_WAIT);
    expect(savedTexts).toEqual([]);
    expect(
      await screen.findByText("Banner text", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
  });
});
