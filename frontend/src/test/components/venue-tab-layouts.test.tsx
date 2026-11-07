import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import VenueTab from "../../components/kp-manage/VenueTab";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import {
  testEditableLayout,
  testLayoutId,
  testMainZone,
} from "../fixtures/venue";

const layoutsUrl = `${testBackendUrl}/api/kp/events/${testEventId}/venue-layouts`;
const layoutUrl = `${testBackendUrl}/api/kp/venue-layouts/${testLayoutId}`;

let createdPayload: unknown = null;
let patchedPayload: unknown = null;
let deleteCalls = 0;

beforeEach(() => {
  createdPayload = null;
  patchedPayload = null;
  deleteCalls = 0;
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(layoutsUrl, () => HttpResponse.json([testEditableLayout])),
    http.post(layoutsUrl, async ({ request }) => {
      createdPayload = await request.json();
      return HttpResponse.json(testEditableLayout);
    }),
    http.patch(layoutUrl, async ({ request }) => {
      patchedPayload = await request.json();
      return HttpResponse.json({ ...testEditableLayout, is_active: false });
    }),
    http.delete(layoutUrl, () => {
      deleteCalls += 1;
      return new HttpResponse(null, { status: 204 });
    }),
  );
});

describe("the venue layout list", () => {
  it("lists the layouts of the event with their size", async () => {
    renderWithProviders(<VenueTab eventId={testEventId} />);

    expect(
      await screen.findByText(testEditableLayout.name),
    ).toBeInTheDocument();
    expect(screen.getByText("kp.venue.layout_size")).toBeInTheDocument();
  });

  it("creates a layout with the entered name and size", async () => {
    const { user } = renderWithProviders(<VenueTab eventId={testEventId} />);

    await screen.findByText(testEditableLayout.name);
    await user.click(
      screen.getByRole("button", { name: "kp.venue.layout_add" }),
    );
    await user.type(
      await screen.findByLabelText("kp.venue.layout_name"),
      "Zweistein",
    );
    const width = screen.getByLabelText("kp.venue.layout_width");
    await user.clear(width);
    await user.type(width, "1200");
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "kp.venue.layout_add",
      }),
    );

    await waitFor(() => {
      expect(createdPayload).toEqual({
        name: "Zweistein",
        width: 1200,
        height: 700,
        order: 1,
        floor_plan: null,
      });
    });
  });

  it("creates a layout on a floor plan without asking for its size", async () => {
    const { user } = renderWithProviders(<VenueTab eventId={testEventId} />);

    await screen.findByText(testEditableLayout.name);
    await user.click(
      screen.getByRole("button", { name: "kp.venue.layout_add" }),
    );
    await user.type(
      await screen.findByLabelText("kp.venue.layout_name"),
      "Main hall",
    );
    await user.click(
      screen.getByLabelText("kp.venue.floor_plan", { selector: "input" }),
    );
    await user.click(
      await screen.findByRole("option", {
        name: "kp.venue.floor_plan_main_hall",
      }),
    );

    expect(
      screen.queryByLabelText("kp.venue.layout_width"),
    ).not.toBeInTheDocument();

    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "kp.venue.layout_add",
      }),
    );

    await waitFor(() => {
      expect(createdPayload).toEqual({
        name: "Main hall",
        order: 1,
        floor_plan: "main_hall",
      });
    });
  });

  it("offers no background upload", async () => {
    const { container } = renderWithProviders(
      <VenueTab eventId={testEventId} />,
    );

    await screen.findByText(testEditableLayout.name);

    expect(container.querySelector('input[type="file"]')).toBeNull();
    expect(
      screen.queryByRole("button", { name: /background/ }),
    ).not.toBeInTheDocument();
  });

  it("hides a layout from companies when the switch is turned off", async () => {
    const { user } = renderWithProviders(<VenueTab eventId={testEventId} />);

    await screen.findByText(testEditableLayout.name);
    await user.click(screen.getByLabelText("kp.venue.layout_active"));

    await waitFor(() => {
      expect(patchedPayload).toEqual({ is_active: false });
    });
  });

  it("deletes a layout only after the confirmation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { user } = renderWithProviders(<VenueTab eventId={testEventId} />);

    await screen.findByText(testEditableLayout.name);
    await user.click(
      screen.getByRole("button", { name: "kp.venue.layout_delete" }),
    );
    expect(deleteCalls).toBe(0);

    confirmSpy.mockReturnValue(true);
    await user.click(
      screen.getByRole("button", { name: "kp.venue.layout_delete" }),
    );

    await waitFor(() => {
      expect(deleteCalls).toBe(1);
    });
  });

  it("keeps the unsaved drawing when another layout is deleted", async () => {
    let layouts = ["Aula", "Bibliothek", "Cafeteria"].map((name, order) => ({
      ...testEditableLayout,
      id: `layout-${order}`,
      name,
      order,
    }));
    server.use(
      http.get(layoutsUrl, () => HttpResponse.json(layouts)),
      http.get(
        `${testBackendUrl}/api/kp/events/${testEventId}/booth-zones`,
        () => HttpResponse.json([{ ...testMainZone, included_services: [] }]),
      ),
      http.delete(
        `${testBackendUrl}/api/kp/venue-layouts/:id`,
        ({ params }) => {
          layouts = layouts.filter((layout) => layout.id !== params.id);
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const { user } = renderWithProviders(<VenueTab eventId={testEventId} />);

    await user.click(await screen.findByText("Bibliothek"));
    await user.click(
      await screen.findByRole("radio", { name: "kp.venue.tool_rect" }),
    );
    const map = screen.getByRole("group", { name: "kp.venue.map_label" });
    fireEvent.pointerDown(map, { clientX: 100, clientY: 100, pointerId: 1 });
    fireEvent.pointerMove(map, { clientX: 300, clientY: 250, pointerId: 1 });
    fireEvent.pointerUp(map, { clientX: 300, clientY: 250, pointerId: 1 });
    expect(screen.getByText("kp.venue.unsaved_changes")).toBeInTheDocument();

    await user.click(
      screen.getAllByRole("button", { name: "kp.venue.layout_delete" })[2],
    );

    await waitFor(() => expect(screen.queryByText("Cafeteria")).toBeNull());
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(screen.getByText("kp.venue.unsaved_changes")).toBeInTheDocument();
  });
});
