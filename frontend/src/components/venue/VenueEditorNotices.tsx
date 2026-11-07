import { Alert, Text } from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { VenueTool } from "./VenueEditorToolbar";
import {
  MAX_LAYOUT_BOOTHS,
  MAX_LAYOUT_SHAPES,
  MAX_POLYGON_POINTS,
} from "./venue-limits";

interface VenueEditorNoticesProps {
  tool: VenueTool;
  layoutWidth: number;
  layoutHeight: number;
  outsideBoundsCount: number;
  hasShapeCapacity: boolean;
  hasBoothCapacity: boolean;
  hasPolygonPointCapacity: boolean;
  saveErrorCode: string | null;
}

const TOOL_HINTS: Record<VenueTool, string> = {
  select: "kp.venue.select_hint",
  rect: "kp.venue.rect_hint",
  polygon: "kp.venue.polygon_hint",
  booth: "kp.venue.booth_hint",
};

const VenueEditorNotices = ({
  tool,
  layoutWidth,
  layoutHeight,
  outsideBoundsCount,
  hasShapeCapacity,
  hasBoothCapacity,
  hasPolygonPointCapacity,
  saveErrorCode,
}: VenueEditorNoticesProps) => {
  const { t } = useTranslation();

  return (
    <>
      {outsideBoundsCount > 0 ? (
        <Alert color="red" icon={<IconAlertCircle />}>
          {t("kp.venue.outside_layout_hint", {
            count: outsideBoundsCount,
            width: layoutWidth,
            height: layoutHeight,
          })}
        </Alert>
      ) : null}

      {!hasShapeCapacity ? (
        <Alert color="yellow" icon={<IconAlertCircle />}>
          {t("kp.venue.shape_limit_hint", { max: MAX_LAYOUT_SHAPES })}
        </Alert>
      ) : null}

      {!hasBoothCapacity ? (
        <Alert color="yellow" icon={<IconAlertCircle />}>
          {t("kp.venue.booth_limit_hint", { max: MAX_LAYOUT_BOOTHS })}
        </Alert>
      ) : null}

      {!hasPolygonPointCapacity ? (
        <Alert color="yellow" icon={<IconAlertCircle />}>
          {t("kp.venue.polygon_point_limit_hint", { max: MAX_POLYGON_POINTS })}
        </Alert>
      ) : null}

      {saveErrorCode !== null ? (
        <Alert color="red" icon={<IconAlertCircle />}>
          {t(saveErrorCode)}
        </Alert>
      ) : null}

      <Text c="dimmed" size="xs">
        {t(TOOL_HINTS[tool])}
      </Text>
    </>
  );
};

export default VenueEditorNotices;
