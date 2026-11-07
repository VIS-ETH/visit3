import { File as NodeFile } from "node:buffer";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import BoothZonesTab from "../../components/kp-manage/BoothZonesTab";
import type { StaffBoothZoneResponse } from "../../orval/generated/fastAPI.schemas";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { SLOW_TEST_TIMEOUT, SLOW_WAIT } from "../timeouts";

vi.setConfig({ testTimeout: SLOW_TEST_TIMEOUT });

const zonesUrl = `${testBackendUrl}/api/kp/events/${testEventId}/booth-zones`;

const mainHall: StaffBoothZoneResponse = {
  id: "zone-1",
  event_id: testEventId,
  name: "Main Hall",
  description: "",
  color: "#112233",
  order: 1,
  capacity: 10,
  booth_size: 4,
  base_price: 100000,
  registration_open: true,
  layout_description: null,
  layout_url: null,
  included_services: [],
};

let created: Record<string, unknown>[] = [];
let updates = 0;
let listRequests = 0;

const openCreateModal = async (
  user: ReturnType<typeof renderWithProviders>["user"],
) => {
  await user.click(
    await screen.findByRole(
      "button",
      { name: "kp.manage.booth_zones_add" },
      SLOW_WAIT,
    ),
  );
  await user.type(
    await screen.findByRole("textbox", { name: "kp.manage.zone_name" }),
    "Hall B",
  );
};

const submitButton = () =>
  within(screen.getByRole("dialog")).getByRole("button", {
    name: "kp.manage.booth_zones_add",
  });

beforeEach(() => {
  created = [];
  updates = 0;
  listRequests = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/kp/events/:eventId/services`, () =>
      HttpResponse.json([]),
    ),
    http.get(zonesUrl, () => {
      listRequests += 1;
      return HttpResponse.json([mainHall]);
    }),
    http.post(zonesUrl, async ({ request }) => {
      created.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json({
        ...mainHall,
        id: `zone-new-${created.length}`,
      });
    }),
    http.patch(`${testBackendUrl}/api/kp/booth-zones/:id`, ({ params }) => {
      updates += 1;
      return HttpResponse.json({ ...mainHall, id: String(params.id) });
    }),
  );
});

describe("saving a booth zone", () => {
  it("keeps submit disabled until the zone list reloaded", async () => {
    server.use(
      http.get(zonesUrl, async () => {
        listRequests += 1;
        if (listRequests > 1) await delay(1500);
        return HttpResponse.json([mainHall]);
      }),
    );
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );

    await openCreateModal(user);
    const submit = submitButton();
    await user.click(submit);
    await waitFor(() => expect(listRequests).toBe(2));

    expect(submit).toBeDisabled();
    await waitFor(
      () => expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
      SLOW_WAIT,
    );
    expect(created).toHaveLength(1);
  });

  it("updates the created zone when saving again after the layout upload failed", async () => {
    let uploads = 0;
    server.use(
      http.put(`${testBackendUrl}/api/kp/booth-zones/:id/layout-file`, () => {
        uploads += 1;
        return HttpResponse.json(
          { code: "error.internal", statusCode: 500 },
          { status: 500 },
        );
      }),
    );
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );

    await openCreateModal(user);
    await user.upload(
      screen
        .getByRole("dialog")
        .querySelector<HTMLInputElement>('input[type="file"]')!,
      new NodeFile(["png"], "layout.png", {
        type: "image/png",
      }) as unknown as File,
    );
    await user.click(submitButton());
    await waitFor(() => expect(uploads).toBe(1), SLOW_WAIT);
    await waitFor(() => expect(submitButton()).toBeEnabled());
    await user.click(submitButton());

    await waitFor(() => expect(uploads).toBe(2), SLOW_WAIT);
    expect(created).toHaveLength(1);
    expect(updates).toBe(1);
  });

  it("sends a whole number as the capacity", async () => {
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );

    await openCreateModal(user);
    const capacity = screen.getByRole("textbox", {
      name: "kp.manage.zone_capacity",
    });
    await user.clear(capacity);
    await user.type(capacity, "2.5");
    await user.click(submitButton());

    await waitFor(() => expect(created).toHaveLength(1));
    expect(Number.isInteger(created[0].capacity)).toBe(true);
  });
});

describe("deleting a booth zone", () => {
  it("sends one delete when the trash icon is confirmed twice", async () => {
    let deletes = 0;
    server.use(
      http.delete(`${testBackendUrl}/api/kp/booth-zones/:id`, async () => {
        deletes += 1;
        await delay(500);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { user } = renderWithProviders(
      <BoothZonesTab eventId={testEventId} />,
    );

    const trash = await screen.findByRole(
      "button",
      { name: "kp.manage.zone_confirm_delete" },
      SLOW_WAIT,
    );
    await user.click(trash);
    await user.click(trash);

    await waitFor(() => expect(trash).toBeEnabled(), SLOW_WAIT);
    expect(deletes).toBe(1);
  });
});
