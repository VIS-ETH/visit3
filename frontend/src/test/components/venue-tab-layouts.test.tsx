import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import VenueTab from "../../components/kp/VenueTab";
import { server } from "../server";
import { testBackendUrl } from "../constants";
import { createToken } from "../jwt";
import { renderWithProviders } from "../render";
import { testEventId } from "../fixtures/kp-booking";
import { testEditableLayout, testLayoutId } from "../fixtures/venue";

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
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
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
      });
    });
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
});
