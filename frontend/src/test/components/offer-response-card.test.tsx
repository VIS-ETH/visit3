import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router";
import OfferResponseCard from "../../components/booking/OfferResponseCard";
import KpCompanyView from "../../pages/KpCompanyView";
import {
  KpBookingStatus,
  type KpResponse,
  type MyBookingResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testBooking, testEvent, testEventId } from "../fixtures/kp-booking";
import {
  installCompanyProfileHandlers,
  profileConfirmCheckbox,
} from "../fixtures/company-profile";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const event: KpResponse = {
  ...testEvent,
  terms_url: "https://vis.ethz.ch/agb",
};

const offered: MyBookingResponse = {
  ...testBooking,
  status: KpBookingStatus.OFFERED,
  offer_deadline: "2099-12-31",
  can_register: false,
};

let acceptRequests: unknown[] = [];
let statusRequests: unknown[] = [];

const renderCard = (booking: MyBookingResponse = offered) =>
  renderWithProviders(<OfferResponseCard event={event} booking={booking} />);

const confirmDialog = async (user: ReturnType<typeof renderCard>["user"]) => {
  await user.click(
    await screen.findByRole("button", { name: "kp.offer.confirm" }, SLOW_WAIT),
  );
  return screen.findByRole("dialog", undefined, SLOW_WAIT);
};

beforeEach(() => {
  acceptRequests = [];
  statusRequests = [];
  localStorage.setItem("token", createToken(3600));
  installCompanyProfileHandlers();
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.post(
      `${testBackendUrl}/api/kp/bookings/:bookingId/accept-offer`,
      async ({ request }) => {
        acceptRequests.push(await request.json());
        return HttpResponse.json({
          ...offered,
          status: KpBookingStatus.REGISTERED,
        });
      },
    ),
    http.patch(
      `${testBackendUrl}/api/kp/bookings/:bookingId/status`,
      async ({ request }) => {
        statusRequests.push(await request.json());
        return HttpResponse.json({
          ...offered,
          status: KpBookingStatus.CANCELLED,
        });
      },
    ),
  );
});

describe("the offered place card", () => {
  it("shows the deadline with a confirm and a decline action", async () => {
    renderCard();

    expect(
      await screen.findByText("kp.offer.title", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "kp.offer.confirm" }),
    ).toBeEnabled();
    expect(
      screen.getByRole("button", { name: "kp.offer.decline" }),
    ).toBeEnabled();
  });

  it("confirms only after the profile, the terms and the binding checkbox", async () => {
    const { user } = renderCard();
    const dialog = await confirmDialog(user);
    const submit = within(dialog).getByRole("button", {
      name: "kp.offer.confirm_submit",
    });

    expect(
      within(dialog).getByRole("link", { name: "kp.booking.confirm_agb_link" }),
    ).toHaveAttribute("href", "https://vis.ethz.ch/agb");
    expect(submit).toBeDisabled();
    await user.click(await profileConfirmCheckbox());
    await user.click(
      within(dialog).getByRole("checkbox", {
        name: /kp\.booking\.confirm_agb_prefix/,
      }),
    );
    expect(submit).toBeDisabled();
    await user.click(
      within(dialog).getByRole("checkbox", {
        name: /kp\.booking\.confirm_binding_checkbox/,
      }),
    );
    expect(submit).toBeEnabled();
    await user.click(submit);

    await waitFor(() =>
      expect(acceptRequests).toEqual([
        { confirm_profile: true, accept_terms: true },
      ]),
    );
  });

  it("declines the offer after a confirmation", async () => {
    const { user } = renderCard();

    await user.click(
      await screen.findByRole(
        "button",
        { name: "kp.offer.decline" },
        SLOW_WAIT,
      ),
    );
    const dialog = await screen.findByRole("dialog", undefined, SLOW_WAIT);
    await user.click(
      within(dialog).getByRole("button", { name: "kp.offer.decline_submit" }),
    );

    await waitFor(() =>
      expect(statusRequests).toEqual([{ status: KpBookingStatus.CANCELLED }]),
    );
  });

  it("hides both actions once the deadline passed", async () => {
    renderCard({ ...offered, offer_deadline: "2000-01-01" });

    expect(
      await screen.findByText("kp.offer.expired", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.offer.confirm" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.offer.decline" }),
    ).not.toBeInTheDocument();
  });
});

describe("the company view with an offered place", () => {
  const renderCompanyView = (booking: MyBookingResponse) => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId`, () =>
        HttpResponse.json(event),
      ),
      http.get(`${testBackendUrl}/api/kp/events/:eventId/my-booking`, () =>
        HttpResponse.json(booking),
      ),
    );
    return renderWithProviders(
      <Routes>
        <Route path="/kp/:id" element={<KpCompanyView />} />
      </Routes>,
      { route: `/kp/${testEventId}` },
    );
  };

  it("asks for a decision instead of offering the booking management", async () => {
    renderCompanyView(offered);

    expect(
      await screen.findByRole(
        "button",
        { name: "kp.offer.confirm" },
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.company_view.manage_booking" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.booking.cancel_action" }),
    ).not.toBeInTheDocument();
  });

  it("explains an expired offer and lets the company book again", async () => {
    renderCompanyView({
      ...offered,
      status: KpBookingStatus.EXPIRED,
      can_register: true,
    });

    expect(
      await screen.findByText("kp.booking.expired_title", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "kp.company_view.restart_booking" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "kp.offer.confirm" }),
    ).not.toBeInTheDocument();
  });
});
