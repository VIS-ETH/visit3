import mainHall from "../../assets/venue/main-hall.webp";
import redHall from "../../assets/venue/red-hall.webp";
import { KpVenueFloorPlan } from "../../orval/generated/fastAPI.schemas";

const FLOOR_PLAN_IMAGES: Record<KpVenueFloorPlan, string> = {
  [KpVenueFloorPlan.main_hall]: mainHall,
  [KpVenueFloorPlan.red_hall]: redHall,
};

export const FLOOR_PLAN_SIZES: Record<
  KpVenueFloorPlan,
  { width: number; height: number }
> = {
  [KpVenueFloorPlan.main_hall]: { width: 1043, height: 655 },
  [KpVenueFloorPlan.red_hall]: { width: 1148, height: 416 },
};

export const FLOOR_PLANS = Object.values(KpVenueFloorPlan);

export const floorPlanImage = (
  floorPlan: KpVenueFloorPlan | null | undefined,
) => (floorPlan ? FLOOR_PLAN_IMAGES[floorPlan] : null);
