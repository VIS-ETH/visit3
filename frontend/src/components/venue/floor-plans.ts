import mainHall from "../../assets/venue/main-hall.webp";
import redHall from "../../assets/venue/red-hall.webp";
import { KpVenueFloorPlan } from "../../orval/generated/fastAPI.schemas";

const FLOOR_PLAN_IMAGES: Record<KpVenueFloorPlan, string> = {
  [KpVenueFloorPlan.main_hall]: mainHall,
  [KpVenueFloorPlan.red_hall]: redHall,
};

export const FLOOR_PLANS = Object.values(KpVenueFloorPlan);

export const floorPlanImage = (
  floorPlan: KpVenueFloorPlan | null | undefined,
) => (floorPlan ? FLOOR_PLAN_IMAGES[floorPlan] : null);
