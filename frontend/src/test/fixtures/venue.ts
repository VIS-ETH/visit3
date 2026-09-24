import { http, HttpResponse } from "msw";
import type {
  BoothZoneWithAvailabilityResult,
  VenueLayoutResponse,
  VenueMapLayoutResult,
  VenueMapResponse,
} from "../../orval/generated/fastAPI.schemas";
import { testBackendUrl } from "../constants";
import { testEventId } from "./kp-booking";

const testMainZoneId = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const testSideZoneId = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
export const testLayoutId = "cccccccc-cccc-cccc-cccc-cccccccccccc";
const testSecondLayoutId = "dddddddd-dddd-dddd-dddd-dddddddddddd";

export const testMainZone: BoothZoneWithAvailabilityResult = {
  id: testMainZoneId,
  event_id: testEventId,
  name: "Einstein",
  description: "Main hall",
  color: "#1f6feb",
  order: 1,
  capacity: 10,
  booth_size: 6,
  base_price: 50000,
  included_services: [],
  is_full: false,
};

export const testSideZone: BoothZoneWithAvailabilityResult = {
  id: testSideZoneId,
  event_id: testEventId,
  name: "Polymensa",
  description: "Side hall",
  color: "#f97316",
  order: 2,
  capacity: 5,
  booth_size: 4,
  base_price: 30000,
  included_services: [],
  is_full: true,
};

const testVenueLayout: VenueMapLayoutResult = {
  id: testLayoutId,
  event_id: testEventId,
  name: "Einstein",
  order: 1,
  width: 1000,
  height: 700,
  is_active: true,
  background_url: null,
  background_file: null,
  zone_shapes: [
    {
      id: "shape-main",
      layout_id: testLayoutId,
      booth_zone_id: testMainZoneId,
      shape: { type: "rect", x: 50, y: 50, w: 300, h: 200 },
      label_position: null,
    },
    {
      id: "shape-side",
      layout_id: testLayoutId,
      booth_zone_id: testSideZoneId,
      shape: {
        type: "polygon",
        points: [
          [500, 100],
          [800, 100],
          [800, 400],
        ],
      },
      label_position: [600, 200],
    },
  ],
  booths: [
    {
      id: "booth-1",
      layout_id: testLayoutId,
      booth_zone_id: testMainZoneId,
      booth_nr: 1,
      x: 100,
      y: 100,
      rotation: null,
      is_own_booking: false,
    },
  ],
};

export const testSecondVenueLayout: VenueMapLayoutResult = {
  ...testVenueLayout,
  id: testSecondLayoutId,
  name: "Polymensa",
  order: 2,
  zone_shapes: [],
  booths: [],
};

export const testVenueMap: VenueMapResponse = {
  event_id: testEventId,
  layouts: [testVenueLayout],
  zones: [testMainZone, testSideZone],
  own_booking: null,
};

export const testEditableLayout: VenueLayoutResponse = {
  id: testLayoutId,
  event_id: testEventId,
  name: "Einstein",
  order: 1,
  width: 1000,
  height: 700,
  is_active: true,
  background_url: null,
  background_file: null,
  zone_shapes: [],
  booths: [],
};

export const emptyVenueHandler = http.get(
  `${testBackendUrl}/api/kp/events/:eventId/venue`,
  ({ params }) =>
    HttpResponse.json({
      event_id: String(params.eventId),
      layouts: [],
      zones: [],
      own_booking: null,
    }),
);
