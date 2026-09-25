import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import ZoneSwitchCard from "../../components/booking/ZoneSwitchCard";
import {
  KpBookingStatus,
  type BookingUpgradeWaitlistEntryResponse,
  type BoothZoneWithAvailabilityResponse,
  type KpResponse,
} from "../../orval/generated/fastAPI.schemas";
import { getGetMyBookingQueryKey } from "../../orval/generated/kp/kp";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import i18n from "../i18n";
import { createToken } from "../jwt";
import { notificationsShow } from "../notifications";
import { createTestQueryClient, renderWithProviders } from "../render";
import {
  testBooking,
  testBookingId,
  testEvent,
  testEventId,
} from "../fixtures/kp-booking";
import {
  emptyVenueHandler,
  testMainZone,
  testSideZone,
  testVenueMap,
} from "../fixtures/venue";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const openEvent: KpResponse = {
  ...testEvent,
  finalization_deadline: "2099-12-31",
};

const closedEvent: KpResponse = {
  ...testEvent,
  finalization_deadline: "2000-01-01",
};

const currentZone: BoothZoneWithAvailabilityResponse = {
  id: testBooking.booth_zone_id,
  event_id: testEventId,
  name: "Main hall",
  description: "Main hall zone",
  color: "#112233",
  order: 1,
  booth_size: 6,
  base_price: 50000,
  included_services: [],
  is_full: false,
};

const freeZone: BoothZoneWithAvailabilityResponse = {
  ...testMainZone,
  is_full: false,
  base_price: 60000,
};

const fullZone: BoothZoneWithAvailabilityResponse = {
  ...testSideZone,
  is_full: true,
  base_price: 30000,
};

const queuedZone: BoothZoneWithAvailabilityResponse = {
  ...testSideZone,
  id: "99999999-9999-9999-9999-999999999999",
  name: "Hoenggerberg",
  is_full: true,
  base_price: 40000,
};

const queuedEntry: BookingUpgradeWaitlistEntryResponse = {
  id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
  booking_id: testBookingId,
  target_booth_zone_id: queuedZone.id,
  priority_rank: 1,
  target_booth_zone: queuedZone,
  is_full: true,
  position: 2,
};

const switchUrl = `${testBackendUrl}/api/kp/bookings/${testBookingId}/switch-zone`;
const waitlistUrl = `${testBackendUrl}/api/kp/bookings/${testBookingId}/upgrade-waitlist`;

let waitlist: BookingUpgradeWaitlistEntryResponse[] = [];

const installHandlers = () => {
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(
      `${testBackendUrl}/api/kp/events/:eventId/booth-zones/available`,
      () => HttpResponse.json([currentZone, freeZone, fullZone, queuedZone]),
    ),
    http.get(waitlistUrl, () => HttpResponse.json(waitlist)),
    emptyVenueHandler,
  );
};

const renderCard = (event = openEvent, booking = testBooking) =>
  renderWithProviders(<ZoneSwitchCard event={event} booking={booking} />);

const openModal = async (user: UserEvent) => {
  await user.click(
    await screen.findByRole(
      "button",
      { name: "kp.zone_switch.open" },
      SLOW_WAIT,
    ),
  );
  return screen.findByRole(
    "group",
    { name: "kp.zone_switch.zone_list" },
    SLOW_WAIT,
  );
};

const zoneOption = (list: HTMLElement, name: string) =>
  within(list).getByRole("button", { name: new RegExp(name) });

beforeAll(() => {
  i18n.addResource("en", "common", "kp.booth_size", "{{size}} m²");
});

beforeEach(() => {
  waitlist = [];
  localStorage.setItem("token", createToken(3600));
  installHandlers();
});

describe("the zone switch card", () => {
  it("lists the other zones with the action that fits their availability", async () => {
    waitlist = [queuedEntry];
    const { user } = renderCard();

    const list = await openModal(user);
    expect(within(list).queryByText(currentZone.name)).not.toBeInTheDocument();
    expect(zoneOption(list, freeZone.name)).toHaveTextContent(
      `${freeZone.booth_size} m²`,
    );
    expect(zoneOption(list, fullZone.name)).toHaveTextContent(
      "kp.zone_switch.zone_full",
    );

    await user.click(zoneOption(list, freeZone.name));
    expect(
      screen.getByRole("button", { name: "kp.zone_switch.switch_action" }),
    ).toBeEnabled();

    await user.click(zoneOption(list, fullZone.name));
    expect(
      screen.getByRole("button", { name: "kp.zone_switch.waitlist_action" }),
    ).toBeEnabled();

    await user.click(zoneOption(list, queuedZone.name));
    expect(
      screen.getByRole("button", { name: "kp.zone_switch.waitlist_action" }),
    ).toBeDisabled();
  });

  it("switches to the selected zone and refreshes the booking", async () => {
    let payload: unknown = null;
    server.use(
      http.post(switchUrl, async ({ request }) => {
        payload = await request.json();
        return HttpResponse.json({
          ...testBooking,
          booth_zone_id: freeZone.id,
        });
      }),
    );
    const queryClient = createTestQueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { user } = renderWithProviders(
      <ZoneSwitchCard event={openEvent} booking={testBooking} />,
      { queryClient },
    );

    const list = await openModal(user);
    await user.click(zoneOption(list, freeZone.name));
    await user.click(
      screen.getByRole("button", { name: "kp.zone_switch.switch_action" }),
    );
    expect(screen.getByText("kp.zone_switch.confirm_body")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "kp.zone_switch.confirm_submit" }),
    );

    await waitFor(() => {
      expect(payload).toEqual({ booth_zone_id: freeZone.id });
    }, SLOW_WAIT);
    await waitFor(() => {
      expect(invalidate).toHaveBeenCalledWith({
        queryKey: getGetMyBookingQueryKey(testEventId),
      });
    }, SLOW_WAIT);
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({ message: "kp.zone_switch.switched" }),
    );
    await waitFor(() => {
      expect(
        screen.queryByRole("group", { name: "kp.zone_switch.zone_list" }),
      ).not.toBeInTheDocument();
    }, SLOW_WAIT);
  });

  it("appends a full zone to the existing waitlist", async () => {
    waitlist = [queuedEntry];
    let payload: unknown = null;
    server.use(
      http.put(waitlistUrl, async ({ request }) => {
        payload = await request.json();
        return HttpResponse.json([queuedEntry]);
      }),
    );
    const { user } = renderCard();

    const list = await openModal(user);
    await user.click(zoneOption(list, fullZone.name));
    await user.click(
      screen.getByRole("button", { name: "kp.zone_switch.waitlist_action" }),
    );

    await waitFor(() => {
      expect(payload).toEqual({
        target_booth_zone_ids: [queuedZone.id, fullZone.id],
      });
    }, SLOW_WAIT);
    expect(notificationsShow).toHaveBeenCalledWith(
      expect.objectContaining({ message: "kp.zone_switch.waitlist_added" }),
    );
  });

  it("shows the error code when the target zone filled up", async () => {
    server.use(
      http.post(switchUrl, () =>
        HttpResponse.json(
          { statusCode: 409, code: "error.kp_booth_zone_full" },
          { status: 409 },
        ),
      ),
    );
    const { user } = renderCard();

    const list = await openModal(user);
    await user.click(zoneOption(list, freeZone.name));
    await user.click(
      screen.getByRole("button", { name: "kp.zone_switch.switch_action" }),
    );
    await user.click(
      screen.getByRole("button", { name: "kp.zone_switch.confirm_submit" }),
    );

    expect(
      await screen.findByText("error.kp_booth_zone_full", undefined, SLOW_WAIT),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "kp.zone_switch.zone_list" }),
    ).toBeInTheDocument();
  });

  it("shows the error code when a queued zone still has capacity", async () => {
    server.use(
      http.put(waitlistUrl, () =>
        HttpResponse.json(
          { statusCode: 400, code: "error.kp_waitlist_zone_has_capacity" },
          { status: 400 },
        ),
      ),
    );
    const { user } = renderCard();

    const list = await openModal(user);
    await user.click(zoneOption(list, fullZone.name));
    await user.click(
      screen.getByRole("button", { name: "kp.zone_switch.waitlist_action" }),
    );

    expect(
      await screen.findByText(
        "error.kp_waitlist_zone_has_capacity",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
  });

  it.each([
    ["before", () => openEvent],
    ["after", () => closedEvent],
  ])(
    "locks the zone once VIS confirmed the booking %s the deadline",
    async (_, event) => {
      renderCard(event(), {
        ...testBooking,
        status: KpBookingStatus.CONFIRMED,
      });

      expect(
        await screen.findByRole(
          "button",
          { name: "kp.zone_switch.open" },
          SLOW_WAIT,
        ),
      ).toBeDisabled();
      expect(
        screen.getByText("kp.zone_switch.disabled_confirmed"),
      ).toBeInTheDocument();
    },
  );

  it("disables the switch once the finalization deadline has passed", async () => {
    renderCard(closedEvent);

    expect(
      await screen.findByRole(
        "button",
        { name: "kp.zone_switch.open" },
        SLOW_WAIT,
      ),
    ).toBeDisabled();
    expect(
      screen.getByText("kp.zone_switch.disabled_deadline"),
    ).toBeInTheDocument();
  });

  it("selects the zone that was picked on the venue map", async () => {
    server.use(
      http.get(`${testBackendUrl}/api/kp/events/:eventId/venue`, () =>
        HttpResponse.json(testVenueMap),
      ),
    );
    const { user } = renderCard();

    await openModal(user);
    await user.click(
      await screen.findByRole("button", { name: testSideZone.name }, SLOW_WAIT),
    );

    expect(
      await screen.findByRole(
        "button",
        {
          name: "kp.zone_switch.waitlist_action",
        },
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
  });
});
