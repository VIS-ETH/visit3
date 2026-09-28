import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import WaitlistCard from "../../components/booking/WaitlistCard";
import {
  KpBookingStatus,
  type BookingUpgradeWaitlistEntryResponse,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import i18n from "../i18n";
import { createToken } from "../jwt";
import { notificationsShow } from "../notifications";
import { renderWithProviders } from "../render";
import { testBooking, testBookingId, testEvent } from "../fixtures/kp-booking";
import { testMainZone, testSideZone } from "../fixtures/venue";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const openEvent: KpResponse = {
  ...testEvent,
  finalization_deadline: "2099-12-31",
};

const einsteinEntry: BookingUpgradeWaitlistEntryResponse = {
  id: "aaaa1111-aaaa-1111-aaaa-111111111111",
  booking_id: testBookingId,
  target_booth_zone_id: testMainZone.id,
  priority_rank: 1,
  target_booth_zone: { ...testMainZone, base_price: 60000 },
  is_full: true,
  position: 1,
};

const polymensaEntry: BookingUpgradeWaitlistEntryResponse = {
  id: "bbbb2222-bbbb-2222-bbbb-222222222222",
  booking_id: testBookingId,
  target_booth_zone_id: testSideZone.id,
  priority_rank: 2,
  target_booth_zone: testSideZone,
  is_full: true,
  position: 3,
};

const waitlistUrl = `${testBackendUrl}/api/kp/bookings/${testBookingId}/upgrade-waitlist`;

let waitlist: BookingUpgradeWaitlistEntryResponse[] = [];
let waitlistRequests = 0;

const renderCard = (booking = testBooking) =>
  renderWithProviders(<WaitlistCard event={openEvent} booking={booking} />);

const actions = (name: string) => screen.getAllByRole("button", { name });

beforeAll(() => {
  i18n.addResource(
    "en",
    "common",
    "kp.waitlist.position",
    "Platz {{position}}",
  );
  i18n.addResource("en", "common", "kp.booth_size", "{{size}} m²");
});

beforeEach(() => {
  waitlist = [einsteinEntry, polymensaEntry];
  waitlistRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(waitlistUrl, () => {
      waitlistRequests += 1;
      return HttpResponse.json(waitlist);
    }),
  );
});

describe("the waitlist card", () => {
  it("shows every queued zone with its position and availability", async () => {
    renderCard();

    expect(
      await screen.findByText("Platz 1", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(screen.getByText("Platz 3")).toBeInTheDocument();
    expect(screen.getByText(testMainZone.name)).toBeInTheDocument();
    expect(screen.getByText(testSideZone.name)).toBeInTheDocument();
    expect(screen.getAllByText("kp.waitlist.zone_full")).toHaveLength(2);
    expect(actions("kp.waitlist.move_up")[0]).toBeDisabled();
    expect(actions("kp.waitlist.move_down")[1]).toBeDisabled();
  });

  it("shows the booth size once a queued zone has free spots", async () => {
    waitlist = [{ ...einsteinEntry, is_full: false }];
    renderCard();

    expect(
      await screen.findByText(`${testMainZone.booth_size} m²`, undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(screen.queryByText("kp.waitlist.zone_full")).not.toBeInTheDocument();
  });

  it("sends the reordered zones when an entry is moved down", async () => {
    let payload: unknown = null;
    server.use(
      http.put(waitlistUrl, async ({ request }) => {
        payload = await request.json();
        waitlist = [polymensaEntry, einsteinEntry];
        return HttpResponse.json(waitlist);
      }),
    );
    const { user } = renderCard();

    await screen.findByText("Platz 1", undefined, SLOW_WAIT);
    await user.click(actions("kp.waitlist.move_down")[0]);

    await waitFor(() => {
      expect(payload).toEqual({
        target_booth_zone_ids: [testSideZone.id, testMainZone.id],
      });
    }, SLOW_WAIT);
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({ message: "kp.waitlist.reordered" }),
    );
    await waitFor(() => {
      expect(waitlistRequests).toBe(2);
    }, SLOW_WAIT);
  });

  it("sends the remaining zones when an entry is removed", async () => {
    let payload: unknown = null;
    server.use(
      http.put(waitlistUrl, async ({ request }) => {
        payload = await request.json();
        waitlist = [einsteinEntry];
        return HttpResponse.json(waitlist);
      }),
    );
    const { user } = renderCard();

    await screen.findByText("Platz 3", undefined, SLOW_WAIT);
    await user.click(actions("kp.waitlist.remove")[1]);

    await waitFor(() => {
      expect(payload).toEqual({
        target_booth_zone_ids: [testMainZone.id],
      });
    }, SLOW_WAIT);
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({ message: "kp.waitlist.removed" }),
    );
  });

  it("shows the error code when the backend rejects the new order", async () => {
    server.use(
      http.put(waitlistUrl, () =>
        HttpResponse.json(
          { statusCode: 400, code: "error.kp_waitlist_same_zone" },
          { status: 400 },
        ),
      ),
    );
    const { user } = renderCard();

    await screen.findByText("Platz 1", undefined, SLOW_WAIT);
    await user.click(actions("kp.waitlist.remove")[0]);

    expect(
      await screen.findByText(
        "error.kp_waitlist_same_zone",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
  });

  it("points to the switch modal while no zone is queued", async () => {
    waitlist = [];
    renderCard();

    expect(
      await screen.findByText("kp.waitlist.empty", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(screen.getByText("kp.waitlist.empty_hint")).toBeInTheDocument();
  });

  it("stays hidden while the booking is no longer registered", () => {
    renderCard({ ...testBooking, status: KpBookingStatus.CONFIRMED });

    expect(screen.queryByText("kp.waitlist.title")).not.toBeInTheDocument();
    expect(waitlistRequests).toBe(0);
  });
});
