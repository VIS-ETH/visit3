import { Image, SimpleGrid, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { FLOOR_PLAN_SIZES, FLOOR_PLANS, floorPlanImage } from "./floor-plans";

interface FloorPlanImagesProps {
  columns?: number;
}

const FloorPlanImages = ({ columns = 1 }: FloorPlanImagesProps) => {
  const { t } = useTranslation();

  return (
    <SimpleGrid cols={{ base: 1, sm: columns }} spacing="md">
      {FLOOR_PLANS.map((floorPlan) => (
        <Stack key={floorPlan} gap={6}>
          <Text fw={600} size="sm">
            {t(`kp.venue.floor_plan_${floorPlan}`)}
          </Text>
          <Image
            src={floorPlanImage(floorPlan)}
            alt={t(`kp.venue.floor_plan_${floorPlan}_alt`)}
            width={FLOOR_PLAN_SIZES[floorPlan].width}
            height={FLOOR_PLAN_SIZES[floorPlan].height}
            w="100%"
            h="auto"
            radius="md"
          />
        </Stack>
      ))}
    </SimpleGrid>
  );
};

export default FloorPlanImages;
