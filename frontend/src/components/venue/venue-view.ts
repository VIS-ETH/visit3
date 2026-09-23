import { clamp, type VenuePoint } from "./venue-geometry";

export interface VenueView {
  scale: number;
  x: number;
  y: number;
}

const MIN_VENUE_SCALE = 0.5;

const MAX_VENUE_SCALE = 8;

export const ZOOM_STEP = 1.25;

export const identityVenueView: VenueView = { scale: 1, x: 0, y: 0 };

export const venueViewTransform = (view: VenueView) =>
  `translate(${view.x} ${view.y}) scale(${view.scale})`;

export const viewBoxToVenuePoint = (
  view: VenueView,
  [x, y]: VenuePoint,
): VenuePoint => [(x - view.x) / view.scale, (y - view.y) / view.scale];

export const zoomVenueView = (
  view: VenueView,
  factor: number,
  focus: VenuePoint,
): VenueView => {
  const scale = clamp(view.scale * factor, MIN_VENUE_SCALE, MAX_VENUE_SCALE);
  const [venueX, venueY] = viewBoxToVenuePoint(view, focus);
  return {
    scale,
    x: focus[0] - venueX * scale,
    y: focus[1] - venueY * scale,
  };
};

export const panVenueView = (
  view: VenueView,
  deltaX: number,
  deltaY: number,
): VenueView => ({ ...view, x: view.x + deltaX, y: view.y + deltaY });
