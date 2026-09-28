import { describe, expect, it } from "vitest";
import {
  isShapeInsideBounds,
  pointInPolygon,
  pointInShape,
  polygonCentroid,
  rectFromPoints,
  rectToPoints,
  shapeBounds,
  shapeCentroid,
  snapPoint,
  snapValue,
  translateShapeInsideBounds,
  type VenuePoint,
} from "../../components/venue/venue-geometry";
import {
  identityVenueView,
  viewBoxToVenuePoint,
  zoomVenueView,
} from "../../components/venue/venue-view";

const triangle: VenuePoint[] = [
  [0, 0],
  [100, 0],
  [0, 100],
];

describe("venue geometry", () => {
  it("turns a rect into its four corner points", () => {
    expect(rectToPoints({ type: "rect", x: 10, y: 20, w: 30, h: 40 })).toEqual([
      [10, 20],
      [40, 20],
      [40, 60],
      [10, 60],
    ]);
  });

  it("puts the centroid of a rect in its middle", () => {
    expect(shapeCentroid({ type: "rect", x: 10, y: 20, w: 30, h: 40 })).toEqual(
      [25, 40],
    );
  });

  it("computes the area weighted centroid of a polygon", () => {
    const [x, y] = polygonCentroid(triangle);
    expect(x).toBeCloseTo(100 / 3);
    expect(y).toBeCloseTo(100 / 3);
  });

  it("falls back to the average point for a degenerate polygon", () => {
    expect(
      polygonCentroid([
        [0, 0],
        [10, 10],
        [20, 20],
      ]),
    ).toEqual([10, 10]);
  });

  it("detects points inside and outside a polygon", () => {
    expect(pointInPolygon([10, 10], triangle)).toBe(true);
    expect(pointInPolygon([90, 90], triangle)).toBe(false);
  });

  it("detects points inside and outside a rect shape", () => {
    const rect = { type: "rect", x: 0, y: 0, w: 50, h: 50 } as const;
    expect(pointInShape([25, 25], rect)).toBe(true);
    expect(pointInShape([75, 25], rect)).toBe(false);
  });

  it("snaps values and points to the grid", () => {
    expect(snapValue(13, 10)).toBe(10);
    expect(snapValue(16, 10)).toBe(20);
    expect(snapValue(16, 0)).toBe(16);
    expect(snapPoint([13, 27], 10)).toEqual([10, 30]);
  });

  it("normalises a rect drawn from bottom right to top left", () => {
    expect(rectFromPoints([100, 80], [40, 20])).toEqual({
      type: "rect",
      x: 40,
      y: 20,
      w: 60,
      h: 60,
    });
  });

  it("reports the bounds of a polygon", () => {
    expect(shapeBounds({ type: "polygon", points: triangle })).toEqual({
      minX: 0,
      minY: 0,
      maxX: 100,
      maxY: 100,
    });
  });

  it("keeps a translated shape inside the layout bounds", () => {
    const moved = translateShapeInsideBounds(
      { type: "rect", x: 900, y: 600, w: 100, h: 100 },
      500,
      500,
      1000,
      700,
    );
    expect(moved).toEqual({ type: "rect", x: 900, y: 600, w: 100, h: 100 });
    expect(isShapeInsideBounds(moved, 1000, 700)).toBe(true);
  });
});

describe("venue view", () => {
  it("keeps the focus point fixed while zooming", () => {
    const zoomed = zoomVenueView(identityVenueView, 2, [500, 350]);
    expect(zoomed.scale).toBe(2);
    expect(viewBoxToVenuePoint(zoomed, [500, 350])).toEqual([500, 350]);
  });

  it("clamps the zoom to the allowed range", () => {
    expect(zoomVenueView(identityVenueView, 100, [0, 0]).scale).toBe(8);
    expect(zoomVenueView(identityVenueView, 0.001, [0, 0]).scale).toBe(0.5);
  });
});
