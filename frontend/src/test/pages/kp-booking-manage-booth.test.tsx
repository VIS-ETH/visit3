import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import KpBookingManage from "../../pages/KpBookingManage";
import { KpServiceCategory } from "../../orval/generated/fastAPI.schemas";
import type {
  BookingResponse,
  ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
import i18n from "../i18n";
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

const bookedService = testBooking.services![0];

const serviceDefaults = {
  event_id: testEventId,
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  max_total_quantity: 0,
  remaining_total_quantity: null,
  is_active: true,
  requirements: [],
};

const powerSocket: ServiceResponse = {
  ...serviceDefaults,
  id: "service-power",
  name: "Power Socket",
  category: KpServiceCategory.SERVICE,
  unit_label: null,
  price: 2500,
  max_quantity_per_booking: 3,
};

const chair: ServiceResponse = {
  ...serviceDefaults,
  id: "booth-chair",
  name: "Stuhl",
  category: KpServiceCategory.BOOTH_ELEMENT,
  unit_label: "Stück",
  price: 1500,
  max_quantity_per_booking: 6,
  remaining_total_quantity: 4,
};

const booking: BookingResponse = {
  ...testBooking,
  services: [
    {
      ...bookedService,
      id: "booking-service-chair",
      service_id: chair.id,
      quantity: 2,
      included_quantity: 2,
      charged_quantity: 0,
      unit_price: chair.price,
      line_net: 0,
      service: chair,
    },
  ],
};

const managePath = "/kp/:id/booking/:bookingId/manage/services";
const manageRoute = `/kp/${testEventId}/booking/${testBookingId}/manage/services`;

let addedPayload: unknown = null;

const renderManage = () =>
  renderWithProviders(
    <Routes>
      <Route path={managePath} element={<KpBookingManage />} />
    </Routes>,
    { route: manageRoute },
  );

beforeAll(() => {
  i18n.addResource(
    "en",
    "common",
    "kp.booking.service_included_note",
    "{{included}} included",
  );
  i18n.addResource(
    "en",
    "common",
    "kp.booking.service_quantity_with_unit",
    "Quantity ({{unit}})",
  );
  i18n.addResource(
    "en",
    "common",
    "kp.booking.service_remaining_total",
    "{{remaining}} still available",
  );
});

beforeEach(() => {
  addedPayload = null;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
      HttpResponse.json(testEvent),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
      HttpResponse.json(booking),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/services/available`,
      () => HttpResponse.json([powerSocket, chair]),
    ),
    http.get(
      `${testBackendUrl}/api/kp/booking-services/:bookingServiceId/requirements/:requirementId/file`,
      () => HttpResponse.json(null),
    ),
    http.post(
      `${testBackendUrl}/api/kp/bookings/:bookingId/services`,
      async ({ request }) => {
        addedPayload = await request.json();
        return HttpResponse.json(booking);
      },
    ),
  );
});

describe("the add services form on the manage page", () => {
  it("splits the catalogue into a services and a booth equipment tab", async () => {
    const { user } = renderManage();

    await screen.findByText(powerSocket.name, undefined, SLOW_WAIT);

    expect(screen.queryByLabelText("Quantity (Stück)")).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("tab", {
        name: "kp.booking_manage.add_services_tab_booth_elements",
      }),
    );

    const boothPanel = within(screen.getByRole("tabpanel"));
    expect(boothPanel.getByLabelText("Quantity (Stück)")).toHaveValue("2");
    expect(boothPanel.getByText("2 included")).toBeInTheDocument();
    expect(boothPanel.getByText("4 still available")).toBeInTheDocument();
  });

  it("adds only the units on top of the booked ones", async () => {
    const { user } = renderManage();

    await screen.findByText(powerSocket.name, undefined, SLOW_WAIT);
    await user.click(
      screen.getByRole("tab", {
        name: "kp.booking_manage.add_services_tab_booth_elements",
      }),
    );
    const chairInput = screen.getByLabelText("Quantity (Stück)");
    await user.clear(chairInput);
    await user.type(chairInput, "4");

    expect(
      screen.getByText("kp.booking.service_line_total"),
    ).toBeInTheDocument();
    expect(screen.getByText("CHF 30.00")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "kp.booking_manage.add_services_submit",
      }),
    );
    await user.click(
      screen.getByRole("button", {
        name: "kp.booking_manage.confirm_add_services_submit",
      }),
    );

    await waitFor(() => {
      expect(addedPayload).toEqual({
        services: [{ service_id: chair.id, quantity: 2 }],
      });
    }, SLOW_WAIT);
  });
});
