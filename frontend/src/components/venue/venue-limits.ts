import type { VenueDraft } from "./venue-draft";
import { isShapeInsideBounds } from "./venue-geometry";

export const MAX_POLYGON_POINTS = 200;
export const MAX_LAYOUT_SHAPES = 500;
export const MAX_LAYOUT_BOOTHS = 500;

interface VenueLayoutBounds {
  width: number;
  height: number;
}

export const countOutsideBounds = (
  draft: VenueDraft,
  { width, height }: VenueLayoutBounds,
) =>
  draft.shapes.filter(
    (shape) => !isShapeInsideBounds(shape.shape, width, height),
  ).length +
  draft.booths.filter(
    (booth) =>
      booth.x < 0 || booth.y < 0 || booth.x > width || booth.y > height,
  ).length;
