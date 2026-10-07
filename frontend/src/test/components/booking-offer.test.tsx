import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import BookingsTab from "../../components/BookingsTab";
import BookingOfferCard from "../../components/bookings/BookingOfferCard";
import BookingStatusTimeline from "../../components/bookings/BookingStatusTimeline";
import OfferBookingModal from "../../components/bookings/OfferBookingModal";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { KpBookingStatus } from "../../orval/generated/fastAPI.schemas";
import {
  acmeBooking,
  staffBookings,
  testMainHallZone,
  testSideHallZone,
} from "../fixtures/staff-bookings";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const companyId = "cccc0000-0000-0000-0000-000000000001";

let offerRequests: unknown[] = [];
let deadlineRequests: { bookingId: string; body: unknown }[] = [];

beforeEach(() => {
  offerRequests = [];
  deadlineRequests = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/company/management/companies`, () =>
      HttpResponse.json([
        {
          id: companyId,
          name: "Offered AG",
          users_count: 1,
          bookings_count: 0,
        },
      ]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/booth-zones`, () =>
      HttpResponse.json([testMainHallZone, testSideHallZone]),
    ),
    http.post(
      `${testBackendUrl}/api/kp/events/:eventId/bookings/offer`,
      async ({ request }) => {
        offerRequests.push(await request.json());
        return HttpResponse.json(acmeBooking);
      },
    ),
    http.patch(
      `${testBackendUrl}/api/kp/bookings/:bookingId/offer`,
      async ({ params, request }) => {
        const body = (await request.json()) as { deadline: string };
        deadlineRequests.push({ bookingId: String(params.bookingId), body });
        return HttpResponse.json({
          ...acmeBooking,
          status: KpBookingStatus.OFFERED,
          offer_deadline: body.deadline,
        });
      },
    ),
  );
});

describe("the offer place form", () => {
  it("offers the chosen zone to the chosen company", async () => {
    const onClose = vi.fn();
    const { user } = renderWithProviders(
      <OfferBookingModal eventId={testEventId} opened onClose={onClose} />,
    );

    await user.click(
      await screen.findByRole(
        "combobox",
        { name: "kp.manage.booking_company" },
        SLOW_WAIT,
      ),
    );
    await user.click(await screen.findByRole("option", { name: "Offered AG" }));
    await user.click(
      screen.getByRole("combobox", { name: "kp.manage.booking_booth_zone" }),
    );
    await user.click(await screen.findByRole("option", { name: "Side hall" }));
    await user.type(
      screen.getByRole("textbox", { name: "kp.manage.offer_deadline" }),
      "05.10.2026",
    );
    await user.click(
      screen.getByRole("button", { name: "kp.manage.offer_button" }),
    );

    await waitFor(() =>
      expect(offerRequests).toEqual([
        {
          company_id: companyId,
          booth_zone_id: testSideHallZone.id,
          deadline: "2026-10-05",
        },
      ]),
    );
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("keeps the form open and names the reason of a refused offer", async () => {
    server.use(
      http.post(`${testBackendUrl}/api/kp/events/:eventId/bookings/offer`, () =>
        HttpResponse.json(
          { code: "error.kp_booth_zone_at_capacity" },
          { status: 409 },
        ),
      ),
    );
    const onClose = vi.fn();
    const { user } = renderWithProviders(
      <OfferBookingModal eventId={testEventId} opened onClose={onClose} />,
    );

    await user.click(
      await screen.findByRole(
        "combobox",
        { name: "kp.manage.booking_company" },
        SLOW_WAIT,
      ),
    );
    await user.click(await screen.findByRole("option", { name: "Offered AG" }));
    await user.click(
      screen.getByRole("combobox", { name: "kp.manage.booking_booth_zone" }),
    );
    await user.click(await screen.findByRole("option", { name: "Main hall" }));
    await user.type(
      screen.getByRole("textbox", { name: "kp.manage.offer_deadline" }),
      "05.10.2026",
    );
    await user.click(
      screen.getByRole("button", { name: "kp.manage.offer_button" }),
    );

    expect(
      await screen.findByText("error.kp_booth_zone_at_capacity"),
    ).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("waits for a valid deadline before offering", async () => {
    const { user } = renderWithProviders(
      <OfferBookingModal eventId={testEventId} opened onClose={vi.fn()} />,
    );

    await user.type(
      await screen.findByRole(
        "textbox",
        { name: "kp.manage.offer_deadline" },
        SLOW_WAIT,
      ),
      "31.02.2026",
    );

    expect(
      screen.getByRole("button", { name: "kp.manage.offer_button" }),
    ).toBeDisabled();
  });
});

describe("offered bookings in the staff list", () => {
  beforeEach(() => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId/bookings`, () =>
        HttpResponse.json(
          staffBookings.map((booking) =>
            booking.id === acmeBooking.id
              ? {
                  ...booking,
                  status: KpBookingStatus.OFFERED,
                  offer_deadline: "2026-10-05",
                }
              : booking,
          ),
        ),
      ),
    );
  });

  it("marks only the offered booking as pending with its deadline", async () => {
    renderWithProviders(<BookingsTab eventId={testEventId} canOffer />);

    expect(
      await screen.findAllByText("kp.manage.offer_until", undefined, SLOW_WAIT),
    ).toHaveLength(1);
    expect(
      within(screen.getByRole("table")).getAllByText(
        "kp.booking.status.offered.label",
      ),
    ).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: "kp.manage.offer_button" }),
    ).toBeInTheDocument();
  });

  it("hides the offer action from staff without the president role", async () => {
    renderWithProviders(<BookingsTab eventId={testEventId} />);

    expect(
      await screen.findByText("kp.manage.offer_until", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.manage.offer_button" }),
    ).not.toBeInTheDocument();
  });
});

describe("the offer card on the booking page", () => {
  it("moves the confirmation deadline", async () => {
    const { user } = renderWithProviders(
      <BookingOfferCard
        booking={{
          ...acmeBooking,
          status: KpBookingStatus.OFFERED,
          offer_deadline: "2026-10-05",
        }}
        eventId={testEventId}
        canEdit
      />,
    );

    const input = await screen.findByRole(
      "textbox",
      { name: "kp.manage.offer_deadline" },
      SLOW_WAIT,
    );
    expect(input).toHaveValue("05.10.2026");
    await user.clear(input);
    await user.type(input, "09.10.2026");
    await user.click(
      screen.getByRole("button", { name: "kp.manage.offer_save" }),
    );

    await waitFor(() =>
      expect(deadlineRequests).toEqual([
        {
          bookingId: acmeBooking.id,
          body: { deadline: "2026-10-09" },
        },
      ]),
    );
  });

  it("only shows the deadline to staff without the president role", async () => {
    renderWithProviders(
      <BookingOfferCard
        booking={{
          ...acmeBooking,
          status: KpBookingStatus.OFFERED,
          offer_deadline: "2026-10-05",
        }}
        eventId={testEventId}
        canEdit={false}
      />,
    );

    expect(
      await screen.findByText("kp.manage.offer_title", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.manage.offer_save" }),
    ).not.toBeInTheDocument();
  });
});

describe("the status history of an offered place", () => {
  const offered = {
    ...acmeBooking,
    status: KpBookingStatus.OFFERED,
    offer_deadline: "2026-10-05",
    confirmed_at: null,
  };

  it("starts with the offer and keeps the registration open", () => {
    renderWithProviders(<BookingStatusTimeline booking={offered} />);

    expect(
      screen.getByText("kp.manage.booking_timeline_offered"),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText("kp.manage.booking_timeline_pending"),
    ).toHaveLength(2);
  });

  it("ends an expired offer without a registration", () => {
    renderWithProviders(
      <BookingStatusTimeline
        booking={{ ...offered, status: KpBookingStatus.EXPIRED }}
      />,
    );

    expect(
      screen.getByText("kp.manage.booking_timeline_expired"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("kp.manage.booking_timeline_registered"),
    ).not.toBeInTheDocument();
  });
});
