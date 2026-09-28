import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import BoothZonesTab from "../../components/BoothZonesTab";
import type { StaffBoothZoneResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const zone = (id: string, name: string, registrationOpen: boolean) =>
  ({
    id,
    event_id: testEventId,
    name,
    description: "",
    color: "#000001",
    order: 0,
    capacity: 10,
    booth_size: 4,
    base_price: 100000,
    registration_open: registrationOpen,
    layout_description: null,
    layout_url: null,
    included_services: [],
  }) satisfies StaffBoothZoneResponse;

let zones: StaffBoothZoneResponse[] = [];
let updates: { id: string; body: unknown }[] = [];

const registrationSwitches = () =>
  screen.getAllByRole("switch", { name: "kp.manage.zone_registration_open" });

beforeEach(() => {
  zones = [
    zone("zone-main", "Main hall", true),
    zone("zone-side", "Side hall", false),
  ];
  updates = [];
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/${testEventId}/booth-zones`, () =>
      HttpResponse.json(zones),
    ),
    http.get(`${testBackendUrl}/api/kp/events/${testEventId}/services`, () =>
      HttpResponse.json([]),
    ),
    http.patch(
      `${testBackendUrl}/api/kp/booth-zones/:zoneId`,
      async ({ params, request }) => {
        const body = (await request.json()) as { registration_open: boolean };
        updates.push({ id: String(params.zoneId), body });
        zones = zones.map((candidate) =>
          candidate.id === params.zoneId
            ? { ...candidate, registration_open: body.registration_open }
            : candidate,
        );
        return HttpResponse.json(
          zones.find((candidate) => candidate.id === params.zoneId),
        );
      },
    ),
  );
});

describe("the booth zone registration switch", () => {
  it("shows whether each zone takes registrations", async () => {
    renderWithProviders(<BoothZonesTab eventId={testEventId} />);
    await screen.findByText("Side hall", undefined, SLOW_WAIT);

    expect(registrationSwitches()[0]).toBeChecked();
    expect(registrationSwitches()[1]).not.toBeChecked();
  });

  it("closes an open zone through the api", async () => {
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );
    await screen.findByText("Side hall", undefined, SLOW_WAIT);

    await user.click(registrationSwitches()[0]);

    await waitFor(() =>
      expect(updates).toEqual([
        { id: "zone-main", body: { registration_open: false } },
      ]),
    );
    await waitFor(() => expect(registrationSwitches()[0]).not.toBeChecked());
  });

  it("reopens a closed zone through the api", async () => {
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );
    await screen.findByText("Side hall", undefined, SLOW_WAIT);

    await user.click(registrationSwitches()[1]);

    await waitFor(() =>
      expect(updates).toEqual([
        { id: "zone-side", body: { registration_open: true } },
      ]),
    );
  });
});
