import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import BoothZonesTab from "../../components/BoothZonesTab";
import { KpServiceCategory } from "../../orval/generated/fastAPI.schemas";
import type {
  BoothZoneResponse,
  ServiceResponse,
} from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const zonesUrl = `${testBackendUrl}/api/kp/events/${testEventId}/booth-zones`;
const servicesUrl = `${testBackendUrl}/api/kp/events/${testEventId}/services`;

const serviceDefaults = {
  event_id: testEventId,
  description: "",
  image_url: null,
  confirmation_description: null,
  order: 1,
  price: 1500,
  max_total_quantity: 0,
  remaining_total_quantity: null,
  is_active: true,
  requirements: [],
};

const chair: ServiceResponse = {
  ...serviceDefaults,
  id: "booth-chair",
  name: "Stuhl",
  category: KpServiceCategory.BOOTH_ELEMENT,
  unit_label: "Stück",
  max_quantity_per_booking: 4,
};

const table: ServiceResponse = {
  ...serviceDefaults,
  id: "booth-table",
  name: "Tisch",
  category: KpServiceCategory.BOOTH_ELEMENT,
  unit_label: "Stück",
  max_quantity_per_booking: 2,
};

const zone: BoothZoneResponse = {
  id: "zone-1",
  event_id: testEventId,
  name: "Main Hall",
  description: "",
  color: "#112233",
  order: 1,
  capacity: 10,
  booth_size: 4,
  base_price: 100000,
  layout_description: null,
  layout_url: null,
  included_services: [],
};

let updatePayload: unknown = null;
let updateResponse = () => HttpResponse.json(zone);

const openEditModal = async (
  user: ReturnType<typeof renderWithProviders>["user"],
) => {
  await user.click(
    await screen.findByRole(
      "button",
      { name: "kp.manage.booth_zones_edit" },
      SLOW_WAIT,
    ),
  );
  await screen.findByRole(
    "textbox",
    { name: "kp.manage.zone_name" },
    SLOW_WAIT,
  );
};

const saveZone = async (
  user: ReturnType<typeof renderWithProviders>["user"],
) => {
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "kp.manage.booth_zones_edit",
    }),
  );
};

const addInclusion = async (
  user: ReturnType<typeof renderWithProviders>["user"],
  serviceName: string,
) => {
  await user.click(
    screen.getByRole("button", { name: "kp.manage.zone_included_add" }),
  );
  const selects = screen.getAllByRole("combobox", {
    name: "kp.manage.zone_included_service",
  });
  await user.click(selects[selects.length - 1]);
  await user.click(
    await screen.findByRole("option", { name: serviceName }, SLOW_WAIT),
  );
};

beforeEach(() => {
  updatePayload = null;
  updateResponse = () => HttpResponse.json(zone);
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(zonesUrl, () => HttpResponse.json([zone])),
    http.get(servicesUrl, () => HttpResponse.json([chair, table])),
    http.patch(
      `${testBackendUrl}/api/kp/booth-zones/:boothZoneId`,
      async ({ request }) => {
        updatePayload = await request.json();
        return updateResponse();
      },
    ),
  );
});

describe("the included services editor of a booth zone", () => {
  it("sends the inclusions with the zone", async () => {
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );

    await openEditModal(user);
    await addInclusion(user, chair.name);
    const quantity = screen.getByRole("textbox", {
      name: "kp.manage.zone_included_quantity",
    });
    await user.clear(quantity);
    await user.type(quantity, "3");
    await saveZone(user);

    await waitFor(() => {
      expect(updatePayload).toMatchObject({
        included_services: [{ service_id: chair.id, included_quantity: 3 }],
      });
    }, SLOW_WAIT);
  });

  it("does not offer a service that is already included", async () => {
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );

    await openEditModal(user);
    await addInclusion(user, chair.name);
    await user.click(
      screen.getByRole("button", { name: "kp.manage.zone_included_add" }),
    );
    const selects = screen.getAllByRole("combobox", {
      name: "kp.manage.zone_included_service",
    });
    await user.click(selects[1]);

    const options = await screen.findAllByRole("option", undefined, SLOW_WAIT);
    expect(options.map((option) => option.textContent)).toEqual([table.name]);
  });

  it("caps the included quantity at the maximum of the service", async () => {
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );

    await openEditModal(user);
    await addInclusion(user, table.name);
    const quantity = screen.getByRole("textbox", {
      name: "kp.manage.zone_included_quantity",
    });
    await user.clear(quantity);
    await user.type(quantity, String(table.max_quantity_per_booking));
    await user.type(quantity, "5");

    expect(quantity).toHaveValue(String(table.max_quantity_per_booking));
  });

  it("shows the error the backend reports for the inclusions", async () => {
    updateResponse = () =>
      HttpResponse.json(
        { code: "error.kp_included_exceeds_max", statusCode: 400 },
        { status: 400 },
      );
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );

    await openEditModal(user);
    await addInclusion(user, chair.name);
    await saveZone(user);

    const dialog = within(
      await screen.findByRole("dialog", undefined, SLOW_WAIT),
    );
    expect(
      await dialog.findByText(
        "error.kp_included_exceeds_max",
        undefined,
        SLOW_WAIT,
      ),
    ).toBeInTheDocument();
  });
});
