import type { VenueDraftHistory } from "./venue-draft";
import {
  snapValue,
  translateShapeInsideBounds,
  type VenuePoint,
  type VenueShape,
} from "./venue-geometry";

export interface VenueMove {
  kind: "shape" | "label" | "booth";
  key: string;
  start: VenuePoint;
  origin: VenuePoint;
  shape: VenueShape | null;
  base: VenueDraftHistory;
}

interface MoveBounds {
  gridSize: number | null;
  width: number;
  height: number;
  normalise: (point: VenuePoint) => VenuePoint;
}

export function movedHistory(
  move: VenueMove,
  point: VenuePoint,
  { gridSize, width, height, normalise }: MoveBounds,
): VenueDraftHistory {
  const snap = (value: number) =>
    gridSize === null ? value : snapValue(value, gridSize);
  const deltaX = snap(point[0] - move.start[0]);
  const deltaY = snap(point[1] - move.start[1]);
  const moved = normalise([move.origin[0] + deltaX, move.origin[1] + deltaY]);
  const base = move.base.present;
  const present =
    move.kind === "booth"
      ? {
          ...base,
          booths: base.booths.map((booth) =>
            booth.key === move.key
              ? { ...booth, x: moved[0], y: moved[1] }
              : booth,
          ),
        }
      : {
          ...base,
          shapes: base.shapes.map((shape) => {
            if (shape.key !== move.key || move.shape === null) return shape;
            if (move.kind === "shape") {
              return {
                ...shape,
                shape: translateShapeInsideBounds(
                  move.shape,
                  deltaX,
                  deltaY,
                  width,
                  height,
                ),
              };
            }
            return { ...shape, labelPosition: moved };
          }),
        };
  return { past: [...move.base.past, base], present, future: [] };
}
