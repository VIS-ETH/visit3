import type {
  ReplaceVenueBoothsRequest,
  ReplaceVenueZoneShapesRequest,
  VenueLayoutResponse,
} from "../../orval/generated/fastAPI.schemas";
import type { VenuePoint, VenueShape } from "./venue-geometry";

export interface VenueDraftShape {
  key: string;
  zoneId: string;
  shape: VenueShape;
  labelPosition: VenuePoint | null;
}

export interface VenueDraftBooth {
  key: string;
  zoneId: string;
  boothNr: number;
  x: number;
  y: number;
  rotation: number | null;
}

export interface VenueDraft {
  shapes: VenueDraftShape[];
  booths: VenueDraftBooth[];
}

export interface VenueDraftHistory {
  past: VenueDraft[];
  present: VenueDraft;
  future: VenueDraft[];
}

let draftKeyCounter = 0;

export const nextDraftKey = () => {
  draftKeyCounter += 1;
  return `draft-${draftKeyCounter}`;
};

export const draftFromLayout = (layout: VenueLayoutResponse): VenueDraft => ({
  shapes: layout.zone_shapes.map((shape) => ({
    key: shape.id,
    zoneId: shape.booth_zone_id,
    shape: shape.shape,
    labelPosition: shape.label_position,
  })),
  booths: layout.booths.map((booth) => ({
    key: booth.id,
    zoneId: booth.booth_zone_id,
    boothNr: booth.booth_nr,
    x: booth.x,
    y: booth.y,
    rotation: booth.rotation,
  })),
});

export const createDraftHistory = (present: VenueDraft): VenueDraftHistory => ({
  past: [],
  present,
  future: [],
});

export const commitDraft = (
  history: VenueDraftHistory,
  present: VenueDraft,
): VenueDraftHistory => ({
  past: [...history.past, history.present],
  present,
  future: [],
});

export const undoDraft = (history: VenueDraftHistory): VenueDraftHistory => {
  const previous = history.past.at(-1);
  if (previous === undefined) return history;
  return {
    past: history.past.slice(0, -1),
    present: previous,
    future: [history.present, ...history.future],
  };
};

export const redoDraft = (history: VenueDraftHistory): VenueDraftHistory => {
  const next = history.future.at(0);
  if (next === undefined) return history;
  return {
    past: [...history.past, history.present],
    present: next,
    future: history.future.slice(1),
  };
};

const roundCoordinate = (value: number) => Math.round(value * 10) / 10;

const roundPoint = ([x, y]: VenuePoint): VenuePoint => [
  roundCoordinate(x),
  roundCoordinate(y),
];

const roundShape = (shape: VenueShape): VenueShape =>
  shape.type === "rect"
    ? {
        type: "rect",
        x: roundCoordinate(shape.x),
        y: roundCoordinate(shape.y),
        w: roundCoordinate(shape.w),
        h: roundCoordinate(shape.h),
      }
    : { type: "polygon", points: shape.points.map(roundPoint) };

export const shapesRequest = (
  draft: VenueDraft,
): ReplaceVenueZoneShapesRequest => ({
  shapes: draft.shapes.map((shape) => ({
    booth_zone_id: shape.zoneId,
    shape: roundShape(shape.shape),
    label_position:
      shape.labelPosition === null ? null : roundPoint(shape.labelPosition),
  })),
});

export const boothsRequest = (
  draft: VenueDraft,
): ReplaceVenueBoothsRequest => ({
  booths: draft.booths.map((booth) => ({
    booth_zone_id: booth.zoneId,
    booth_nr: booth.boothNr,
    x: roundCoordinate(booth.x),
    y: roundCoordinate(booth.y),
    rotation: booth.rotation === null ? null : roundCoordinate(booth.rotation),
  })),
});

export const nextBoothNumber = (booths: VenueDraftBooth[]) =>
  booths.reduce((highest, booth) => Math.max(highest, booth.boothNr), 0) + 1;

export const isSameDraft = (left: VenueDraft, right: VenueDraft) =>
  JSON.stringify([shapesRequest(left), boothsRequest(left)]) ===
  JSON.stringify([shapesRequest(right), boothsRequest(right)]);
