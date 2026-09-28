import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import BoothZonesTab from "../../components/BoothZonesTab";
import type { StaffBoothZoneResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { notificationsShow } from "../notifications";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const zonesUrl = `${testBackendUrl}/api/kp/events/${testEventId}/booth-zones`;

const zone = (id: string, name: string, order: number) =>
  ({
    id,
    event_id: testEventId,
    name,
    description: "",
    color: `#00000${order}`,
    order,
    capacity: 10,
    booth_size: 4,
    base_price: 100000,
    layout_description: null,
    layout_url: null,
    included_services: [],
  }) satisfies StaffBoothZoneResponse;

const initialZones = [
  zone("zone-main", "Main hall", 0),
  zone("zone-side", "Side hall", 1),
  zone("zone-annex", "Annex", 2),
];

let zones: StaffBoothZoneResponse[] = initialZones;
let orderRequests: unknown[] = [];
let orderResponse: (ids: string[]) => Response;

const reorderedZones = (ids: string[]) =>
  ids.map((id, order) => ({
    ...initialZones.find((candidate) => candidate.id === id)!,
    order,
  }));

const zoneNames = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((row) => row.textContent);

const moveButtons = (name: "zone_move_up" | "zone_move_down") =>
  screen.getAllByRole("button", { name: `kp.manage.${name}` });

beforeEach(() => {
  zones = initialZones;
  orderRequests = [];
  orderResponse = (ids) => {
    zones = reorderedZones(ids);
    return HttpResponse.json(zones);
  };
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(zonesUrl, () => HttpResponse.json(zones)),
    http.get(`${testBackendUrl}/api/kp/events/${testEventId}/services`, () =>
      HttpResponse.json([]),
    ),
    http.put(`${zonesUrl}/order`, async ({ request }) => {
      const body = (await request.json()) as { booth_zone_ids: string[] };
      orderRequests.push(body);
      return orderResponse(body.booth_zone_ids);
    }),
  );
});

describe("the booth zone order", () => {
  it("moves a zone down with the full new order", async () => {
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );
    await screen.findByText("Annex", undefined, SLOW_WAIT);

    await user.click(moveButtons("zone_move_down")[0]);

    await waitFor(() =>
      expect(orderRequests).toEqual([
        { booth_zone_ids: ["zone-side", "zone-main", "zone-annex"] },
      ]),
    );
    await waitFor(() => expect(zoneNames()[0]).toContain("Side hall"));
    expect(zoneNames()[1]).toContain("Main hall");
  });

  it("moves a zone up with the full new order", async () => {
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );
    await screen.findByText("Annex", undefined, SLOW_WAIT);

    await user.click(moveButtons("zone_move_up")[2]);

    await waitFor(() =>
      expect(orderRequests).toEqual([
        { booth_zone_ids: ["zone-main", "zone-annex", "zone-side"] },
      ]),
    );
  });

  it("cannot move the first zone up or the last zone down", async () => {
    renderWithProviders(<BoothZonesTab eventId={testEventId} />);
    await screen.findByText("Annex", undefined, SLOW_WAIT);

    expect(moveButtons("zone_move_up")[0]).toBeDisabled();
    expect(moveButtons("zone_move_down")[2]).toBeDisabled();
    expect(moveButtons("zone_move_up")[1]).toBeEnabled();
    expect(moveButtons("zone_move_down")[1]).toBeEnabled();
  });

  it("keeps the order and reports a rejected reorder", async () => {
    orderResponse = () =>
      HttpResponse.json(
        { code: "error.kp_booth_zone_order_invalid" },
        { status: 400 },
      );
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );
    await screen.findByText("Annex", undefined, SLOW_WAIT);

    await user.click(moveButtons("zone_move_down")[0]);

    await waitFor(() =>
      expect(notificationsShow).toHaveBeenCalledWith(
        expect.objectContaining({ color: "red" }),
      ),
    );
    expect(orderRequests).toHaveLength(1);
    expect(zoneNames()[0]).toContain("Main hall");
  });
});
