import { File as NodeFile } from "node:buffer";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
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

const zonesUrl = `${testBackendUrl}/api/kp/events/${testEventId}/booth-zones`;
const servicesUrl = `${testBackendUrl}/api/kp/events/${testEventId}/services`;

const zone: StaffBoothZoneResponse = {
  id: "zone-1",
  event_id: testEventId,
  name: "Main Hall",
  description: "",
  color: "#112233",
  order: 1,
  capacity: 10,
  booth_size: 4,
  base_price: 100000,
  layout_description: "Corner booth",
  layout_url: "https://files.test/zone-1/layout.png",
  included_services: [],
};

const layoutFileUrl = `${testBackendUrl}/api/kp/booth-zones/${zone.id}/layout-file`;

let updatePayload: unknown = null;
let layoutUploads = 0;
let layoutDeleted = false;

const renderZones = () =>
  renderWithProviders(<BoothZonesTab eventId={testEventId} />);

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

const layoutFileInput = () =>
  screen
    .getByRole("dialog")
    .querySelector<HTMLInputElement>('input[type="file"]')!;

const saveZone = async (
  user: ReturnType<typeof renderWithProviders>["user"],
) => {
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "kp.manage.booth_zones_edit",
    }),
  );
};

beforeEach(() => {
  updatePayload = null;
  layoutUploads = 0;
  layoutDeleted = false;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(zonesUrl, () => HttpResponse.json([zone])),
    http.get(servicesUrl, () => HttpResponse.json([])),
    http.patch(
      `${testBackendUrl}/api/kp/booth-zones/:boothZoneId`,
      async ({ request }) => {
        updatePayload = await request.json();
        return HttpResponse.json(zone);
      },
    ),
    http.put(layoutFileUrl, async ({ request }) => {
      const body = await request.formData();
      expect(body.has("file")).toBe(true);
      layoutUploads += 1;
      return HttpResponse.json(zone);
    }),
    http.delete(layoutFileUrl, () => {
      layoutDeleted = true;
      return HttpResponse.json(zone);
    }),
  );
});

describe("the layout fields of a booth zone", () => {
  it("previews the stored layout and sends the description", async () => {
    const { user } = renderZones();

    await openEditModal(user);
    const dialog = within(screen.getByRole("dialog"));
    expect(
      dialog.getByAltText("kp.manage.zone_layout_preview_alt"),
    ).toHaveAttribute("src", zone.layout_url);
    expect(
      dialog.getByText("kp.manage.zone_layout_allowed_formats"),
    ).toBeInTheDocument();

    const description = dialog.getByRole("textbox", {
      name: "kp.manage.zone_layout_description",
    });
    await user.clear(description);
    await user.type(description, "Two windows");
    await saveZone(user);

    await waitFor(() => {
      expect(updatePayload).toMatchObject({
        layout_description: "Two windows",
      });
    }, SLOW_WAIT);
    expect(layoutUploads).toBe(0);
  });

  it("uploads a replacement layout after saving the zone", async () => {
    const { user } = renderZones();

    await openEditModal(user);
    const dialog = within(screen.getByRole("dialog"));
    await user.upload(
      layoutFileInput(),
      new NodeFile(["plan"], "hall.pdf", {
        type: "application/pdf",
      }) as unknown as File,
    );

    expect(dialog.getByText("hall.pdf")).toBeInTheDocument();
    await saveZone(user);

    await waitFor(() => {
      expect(layoutUploads).toBe(1);
    }, SLOW_WAIT);
    expect(layoutDeleted).toBe(false);
  });

  it("rejects a file format the backend does not store", async () => {
    const { user } = renderZones();

    await openEditModal(user);
    const dialog = within(screen.getByRole("dialog"));
    fireEvent.change(layoutFileInput(), {
      target: {
        files: [new NodeFile(["plan"], "hall.txt", { type: "text/plain" })],
      },
    });

    expect(
      dialog.getByText("kp.manage.zone_layout_file_invalid"),
    ).toBeInTheDocument();
    expect(dialog.queryByText("hall.txt")).not.toBeInTheDocument();
  });

  it("removes the stored layout when it is cleared", async () => {
    const { user } = renderZones();

    await openEditModal(user);
    const dialog = within(screen.getByRole("dialog"));
    await user.click(
      dialog.getByRole("button", { name: "kp.manage.zone_layout_remove" }),
    );

    expect(dialog.getByText("kp.manage.zone_layout_none")).toBeInTheDocument();
    await saveZone(user);

    await waitFor(() => {
      expect(layoutDeleted).toBe(true);
    }, SLOW_WAIT);
    expect(layoutUploads).toBe(0);
  });
});
