import { describe, expect, it } from "vitest";
import { act, fireEvent, screen } from "@testing-library/react";
import VenueLayoutEditor from "../../components/venue/VenueLayoutEditor";
import {
  MAX_LAYOUT_BOOTHS,
  MAX_LAYOUT_SHAPES,
  MAX_POLYGON_POINTS,
} from "../../components/venue/venue-limits";
import type {
  BoothZoneResponse,
  VenueBoothResponse,
  VenueLayoutResponse,
  VenueZoneShapeResponse,
} from "../../orval/generated/fastAPI.schemas";
import { renderWithProviders } from "../render";
import { testEditableLayout, testMainZone } from "../fixtures/venue";

const zones: BoothZoneResponse[] = [
  {
    id: testMainZone.id,
    event_id: testMainZone.event_id,
    name: testMainZone.name,
    description: testMainZone.description,
    color: testMainZone.color,
    order: testMainZone.order,
    booth_size: testMainZone.booth_size,
    base_price: testMainZone.base_price,
    included_services: [],
  },
];

const rectShape = (index: number): VenueZoneShapeResponse => ({
  id: `shape-${index}`,
  layout_id: testEditableLayout.id,
  booth_zone_id: testMainZone.id,
  shape: { type: "rect", x: 0, y: 0, w: 10, h: 10 },
  label_position: null,
});

const booth = (index: number): VenueBoothResponse => ({
  id: `booth-${index}`,
  layout_id: testEditableLayout.id,
  booth_zone_id: testMainZone.id,
  booth_nr: index + 1,
  x: 10,
  y: 10,
  rotation: null,
});

const layoutWith = (
  overrides: Partial<VenueLayoutResponse>,
): VenueLayoutResponse => ({ ...testEditableLayout, ...overrides });

const renderEditor = (layout: VenueLayoutResponse) =>
  renderWithProviders(<VenueLayoutEditor layout={layout} zones={zones} />);

const canvas = () => screen.getByRole("group", { name: "kp.venue.map_label" });

const pointerAt = (target: Element, type: string, x: number, y: number) =>
  fireEvent[type as "pointerDown"](target, {
    clientX: x,
    clientY: y,
    pointerId: 1,
  });

const pointerDownAtGridPoint = (target: Element, index: number) =>
  pointerAt(
    target,
    "pointerDown",
    10 + (index % 50) * 10,
    10 + Math.floor(index / 50) * 10,
  );

const saveButton = () => screen.getByRole("button", { name: "kp.venue.save" });

describe("the venue layout shape limit", () => {
  it("refuses another shape once the maximum is reached", async () => {
    const shapes = Array.from({ length: MAX_LAYOUT_SHAPES }, (_, index) =>
      rectShape(index),
    );
    const { user } = renderEditor(layoutWith({ zone_shapes: shapes }));

    expect(screen.getByText("kp.venue.shape_limit_hint")).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "kp.venue.tool_rect" }));
    pointerAt(canvas(), "pointerDown", 100, 100);
    pointerAt(canvas(), "pointerMove", 300, 250);
    pointerAt(canvas(), "pointerUp", 300, 250);

    expect(
      screen.getAllByRole("button", { name: testMainZone.name }),
    ).toHaveLength(MAX_LAYOUT_SHAPES);
  });

  it("keeps drawing possible below the maximum", async () => {
    const shapes = Array.from({ length: MAX_LAYOUT_SHAPES - 1 }, (_, index) =>
      rectShape(index),
    );
    const { user } = renderEditor(layoutWith({ zone_shapes: shapes }));

    expect(
      screen.queryByText("kp.venue.shape_limit_hint"),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "kp.venue.tool_rect" }));
    pointerAt(canvas(), "pointerDown", 100, 100);
    pointerAt(canvas(), "pointerMove", 300, 250);
    pointerAt(canvas(), "pointerUp", 300, 250);

    expect(
      screen.getAllByRole("button", { name: testMainZone.name }),
    ).toHaveLength(MAX_LAYOUT_SHAPES);
  });
});

describe("the venue layout booth limit", () => {
  it("refuses another booth once the maximum is reached", async () => {
    const booths = Array.from({ length: MAX_LAYOUT_BOOTHS }, (_, index) =>
      booth(index),
    );
    const { user } = renderEditor(layoutWith({ booths }));

    expect(screen.getByText("kp.venue.booth_limit_hint")).toBeInTheDocument();

    await user.click(
      screen.getByRole("radio", { name: "kp.venue.tool_booth" }),
    );
    pointerAt(canvas(), "pointerDown", 200, 200);

    expect(
      screen.queryByRole("button", {
        name: `kp.venue.booth_marker ${MAX_LAYOUT_BOOTHS + 1} ${testMainZone.name}`,
      }),
    ).not.toBeInTheDocument();
  });
});

describe("the venue polygon point limit", () => {
  it("stops collecting points at the maximum", async () => {
    const { user } = renderEditor(testEditableLayout);

    await user.click(
      screen.getByRole("radio", { name: "kp.venue.tool_polygon" }),
    );
    const target = canvas();
    act(() => {
      for (let index = 0; index < MAX_POLYGON_POINTS; index += 1) {
        pointerDownAtGridPoint(target, index);
      }
    });
    for (
      let index = MAX_POLYGON_POINTS;
      index < MAX_POLYGON_POINTS + 5;
      index += 1
    ) {
      pointerDownAtGridPoint(target, index);
    }

    expect(
      screen.getByText("kp.venue.polygon_point_limit_hint"),
    ).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Enter" });

    const shape = screen.getByRole("button", { name: testMainZone.name });
    const points = shape.querySelector("polygon")?.getAttribute("points") ?? "";
    expect(points.split(" ")).toHaveLength(MAX_POLYGON_POINTS);
  });
});

describe("a layout that was resized smaller than its shapes", () => {
  it("warns and blocks saving until the shapes fit", () => {
    renderEditor(
      layoutWith({
        width: 100,
        height: 100,
        zone_shapes: [
          {
            ...rectShape(0),
            shape: { type: "rect", x: 0, y: 0, w: 400, h: 200 },
          },
        ],
        booths: [{ ...booth(0), x: 900, y: 600 }],
      }),
    );

    expect(
      screen.getByText("kp.venue.outside_layout_hint"),
    ).toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
  });

  it("allows saving once everything fits", () => {
    renderEditor(
      layoutWith({
        zone_shapes: [rectShape(0)],
        booths: [booth(0)],
      }),
    );

    expect(
      screen.queryByText("kp.venue.outside_layout_hint"),
    ).not.toBeInTheDocument();
    expect(saveButton()).toBeEnabled();
  });
});
