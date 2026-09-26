import {
  Alert,
  Center,
  Group,
  Loader,
  Paper,
  SegmentedControl,
  Stack,
  Text,
} from "@mantine/core";
import { IconAlertCircle, IconMap } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type {
  BoothZoneWithAvailabilityResult,
  VenueMapLayoutResult,
} from "../../orval/generated/fastAPI.schemas";
import { useGetEventVenue } from "../../orval/generated/kp/kp";
import { formatPrice } from "../../utils/price-utils";
import { KpBoothZoneColorSwatch } from "../KpBoothZoneColorSwatch";
import VenueMapCanvas, {
  type VenueCanvasBooth,
  type VenueCanvasShape,
} from "./VenueMapCanvas";
import { floorPlanImage } from "./floor-plans";

interface VenueBoothHighlight {
  zoneId: string;
  boothNr: number | null;
}

interface VenueMapViewerProps {
  eventId: string;
  selectedZoneId?: string | null;
  onSelectZone?: (zoneId: string) => void;
  highlightBooth?: VenueBoothHighlight | null;
  viewHeight?: number;
}

const byOrder = (a: { order: number }, b: { order: number }) =>
  a.order - b.order;

const legendItemId = (zoneId: string) => `venue-legend-${zoneId}`;

const layoutCoversZone = (layout: VenueMapLayoutResult, zoneId: string) =>
  layout.zone_shapes.some((shape) => shape.booth_zone_id === zoneId);

const VenueMapViewer = ({
  eventId,
  selectedZoneId,
  onSelectZone,
  highlightBooth,
  viewHeight,
}: VenueMapViewerProps) => {
  const { t } = useTranslation();
  const { data: venue, isLoading, isError } = useGetEventVenue(eventId);
  const [pickedLayoutId, setPickedLayoutId] = useState<string | null>(null);

  const layouts = useMemo(
    () => [...(venue?.layouts ?? [])].sort(byOrder),
    [venue],
  );
  const zones = useMemo(() => [...(venue?.zones ?? [])].sort(byOrder), [venue]);
  const layout =
    layouts.find((candidate) => candidate.id === pickedLayoutId) ??
    layouts.at(0);

  useEffect(() => {
    if (!selectedZoneId || layout === undefined) return;
    if (layoutCoversZone(layout, selectedZoneId)) return;
    const match = layouts.find((candidate) =>
      layoutCoversZone(candidate, selectedZoneId),
    );
    if (match) setPickedLayoutId(match.id);
  }, [selectedZoneId, layout, layouts]);

  const zoneCaption = (zone: BoothZoneWithAvailabilityResult) =>
    zone.is_full
      ? t("kp.venue.zone_full")
      : t("kp.booth_size", { size: zone.booth_size });

  const canvasZones = zones.map((zone) => ({
    id: zone.id,
    name: zone.name,
    color: zone.color,
    caption: zoneCaption(zone),
    descriptionId: legendItemId(zone.id),
  }));

  const shapes: VenueCanvasShape[] = (layout?.zone_shapes ?? []).map(
    (shape) => ({
      key: shape.id,
      zoneId: shape.booth_zone_id,
      shape: shape.shape,
      labelPosition: shape.label_position,
    }),
  );

  const booths: VenueCanvasBooth[] = (layout?.booths ?? []).map((booth) => ({
    key: booth.id,
    zoneId: booth.booth_zone_id,
    boothNr: booth.booth_nr,
    x: booth.x,
    y: booth.y,
    rotation: booth.rotation,
    isHighlighted:
      booth.is_own_booking ||
      (highlightBooth?.zoneId === booth.booth_zone_id &&
        highlightBooth.boothNr === booth.booth_nr),
  }));

  if (isLoading) {
    return (
      <Paper withBorder radius="md" p="xl">
        <Center mih={200}>
          <Loader />
        </Center>
      </Paper>
    );
  }

  if (isError) {
    return (
      <Alert icon={<IconAlertCircle />} color="red">
        {t("kp.venue.load_error")}
      </Alert>
    );
  }

  if (layout === undefined) {
    return (
      <Paper withBorder radius="md" p="xl">
        <Stack align="center" gap="xs" mih={200} justify="center">
          <IconMap size={48} style={{ opacity: 0.3 }} />
          <Text c="dimmed" size="sm" ta="center">
            {t("kp.venue.no_layouts")}
          </Text>
        </Stack>
      </Paper>
    );
  }

  return (
    <Stack gap="sm">
      {layouts.length > 1 ? (
        <SegmentedControl
          data={layouts.map((candidate) => ({
            value: candidate.id,
            label: candidate.name,
          }))}
          onChange={setPickedLayoutId}
          value={layout.id}
        />
      ) : null}
      <Paper withBorder radius="md" p="xs">
        <VenueMapCanvas
          floorPlanUrl={floorPlanImage(layout.floor_plan)}
          booths={booths}
          height={layout.height}
          onActivateShape={
            onSelectZone ? (shape) => onSelectZone(shape.zoneId) : undefined
          }
          selectedZoneId={selectedZoneId}
          shapes={shapes}
          viewHeight={viewHeight}
          width={layout.width}
          zones={canvasZones}
        />
      </Paper>
      <Group gap="lg" wrap="wrap">
        {zones.map((zone) => (
          <Group gap={6} id={legendItemId(zone.id)} key={zone.id} wrap="nowrap">
            <KpBoothZoneColorSwatch color={zone.color} />
            <Text fw={500} size="sm">
              {zone.name}
            </Text>
            <Text c="dimmed" size="xs">
              {zoneCaption(zone)}
            </Text>
            <Text c="dimmed" size="xs">
              CHF {formatPrice(zone.base_price)}
            </Text>
          </Group>
        ))}
      </Group>
    </Stack>
  );
};

export default VenueMapViewer;
