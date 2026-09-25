import { beforeEach, describe, expect, it } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import VenueTab from "../../components/kp/VenueTab";
import type {
  BoothZoneResponse,
  ReplaceVenueZoneShapesRequest,
} from "../../orval/generated/fastAPI.schemas";
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

const zone: BoothZoneResponse = {
  id: testMainZone.id,
  event_id: testMainZone.event_id,
  name: testMainZone.name,
  description: testMainZone.description,
  color: testMainZone.color,
  order: testMainZone.order,
  booth_size: testMainZone.booth_size,
  base_price: testMainZone.base_price,
  included_services: [],
};

const shapesUrl = `${testBackendUrl}/api/kp/venue-layouts/${testLayoutId}/shapes`;
const boothsUrl = `${testBackendUrl}/api/kp/venue-layouts/${testLayoutId}/booths`;

let shapesPayload: unknown = null;
let boothsPayload: unknown = null;
let shapesResponse = () => HttpResponse.json(testEditableLayout);

const savedLayout = () => ({
  ...testEditableLayout,
  zone_shapes: (shapesPayload as ReplaceVenueZoneShapesRequest).shapes!.map(
    (shape, index) => ({
      id: `shape-${index}`,
      layout_id: testLayoutId,
      ...shape,
      label_position: shape.label_position ?? null,
    }),
  ),
});

const canvas = () => screen.getByRole("group", { name: "kp.venue.map_label" });

const drawRectangle = async (
  user: ReturnType<typeof renderWithProviders>["user"],
) => {
  await user.click(screen.getByRole("radio", { name: "kp.venue.tool_rect" }));
  const svg = canvas();
  fireEvent.pointerDown(svg, { clientX: 100, clientY: 100, pointerId: 1 });
  fireEvent.pointerMove(svg, { clientX: 300, clientY: 250, pointerId: 1 });
  fireEvent.pointerUp(svg, { clientX: 300, clientY: 250, pointerId: 1 });
};

beforeEach(() => {
  shapesPayload = null;
  boothsPayload = null;
  shapesResponse = () => HttpResponse.json(testEditableLayout);
  localStorage.setItem("token", createToken(3600));
  server.use(
    http.get(`${testBackendUrl}/api/csrftoken`, () =>
      HttpResponse.json({ token: "csrf-1" }),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/venue-layouts`, () =>
      HttpResponse.json([testEditableLayout]),
    ),
    http.get(`${testBackendUrl}/api/kp/events/:eventId/booth-zones`, () =>
      HttpResponse.json([zone]),
    ),
    http.put(shapesUrl, async ({ request }) => {
      shapesPayload = await request.json();
      return shapesResponse();
    }),
    http.put(boothsUrl, async ({ request }) => {
      boothsPayload = await request.json();
      return HttpResponse.json(savedLayout());
    }),
  );
});

describe("saving a venue layout", () => {
  it("sends the drawn shapes and booths to the backend", async () => {
    const { user } = renderWithProviders(<VenueTab eventId={testEventId} />);

    await screen.findByRole("radio", { name: "kp.venue.tool_rect" });
    await drawRectangle(user);
    expect(screen.getByText("kp.venue.unsaved_changes")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "kp.venue.save" }));

    await waitFor(() => {
      expect(shapesPayload).toEqual({
        shapes: [
          {
            booth_zone_id: zone.id,
            shape: { type: "rect", x: 100, y: 100, w: 200, h: 150 },
            label_position: null,
          },
        ],
      });
    });
    await waitFor(() => {
      expect(boothsPayload).toEqual({ booths: [] });
    });
    await waitFor(() => {
      expect(
        screen.queryByText("kp.venue.unsaved_changes"),
      ).not.toBeInTheDocument();
    });
  });

  it("shows the validation error the backend reports", async () => {
    shapesResponse = () =>
      HttpResponse.json(
        { code: "error.kp_venue_out_of_bounds", statusCode: 400 },
        { status: 400 },
      );
    const { user } = renderWithProviders(<VenueTab eventId={testEventId} />);

    await screen.findByRole("radio", { name: "kp.venue.tool_rect" });
    await drawRectangle(user);
    await user.click(screen.getByRole("button", { name: "kp.venue.save" }));

    expect(
      await screen.findByText("error.kp_venue_out_of_bounds"),
    ).toBeInTheDocument();
    expect(boothsPayload).toBeNull();
  });
});
