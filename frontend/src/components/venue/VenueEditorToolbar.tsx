import {
  ActionIcon,
  Badge,
  Button,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  Switch,
} from "@mantine/core";
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconDeviceFloppy,
  IconTrash,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import type { BoothZoneResponse } from "../../orval/generated/fastAPI.schemas";

export type VenueTool = "select" | "rect" | "polygon" | "booth";

const VENUE_TOOLS: readonly VenueTool[] = [
  "select",
  "rect",
  "polygon",
  "booth",
];

interface VenueEditorToolbarProps {
  tool: VenueTool;
  onToolChange: (tool: VenueTool) => void;
  isSnapEnabled: boolean;
  onSnapChange: (enabled: boolean) => void;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  zones: BoothZoneResponse[];
  activeZoneId: string | null;
  onZoneChange: (zoneId: string | null) => void;
  selectedBoothNumber: number | null;
  onBoothNumberChange: (boothNr: number) => void;
  canDeleteSelected: boolean;
  onDeleteSelected: () => void;
  canSave: boolean;
  isSaving: boolean;
  isDirty: boolean;
  onSave: () => void;
}

const VenueEditorToolbar = ({
  tool,
  onToolChange,
  isSnapEnabled,
  onSnapChange,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  zones,
  activeZoneId,
  onZoneChange,
  selectedBoothNumber,
  onBoothNumberChange,
  canDeleteSelected,
  onDeleteSelected,
  canSave,
  isSaving,
  isDirty,
  onSave,
}: VenueEditorToolbarProps) => {
  const { t } = useTranslation();
  const toolLabels: Record<VenueTool, string> = {
    select: t("kp.venue.tool_select"),
    rect: t("kp.venue.tool_rect"),
    polygon: t("kp.venue.tool_polygon"),
    booth: t("kp.venue.tool_booth"),
  };

  return (
    <>
      <Group justify="space-between" wrap="wrap">
        <SegmentedControl
          data={VENUE_TOOLS.map((value) => ({
            value,
            label: toolLabels[value],
          }))}
          onChange={(value) =>
            onToolChange(VENUE_TOOLS.find((item) => item === value) ?? "select")
          }
          value={tool}
        />
        <Group gap="xs">
          <Switch
            checked={isSnapEnabled}
            label={t("kp.venue.snap_grid")}
            onChange={(event) => onSnapChange(event.currentTarget.checked)}
          />
          <ActionIcon
            aria-label={t("kp.venue.undo")}
            disabled={!canUndo}
            onClick={onUndo}
            variant="default"
          >
            <IconArrowBackUp size={16} />
          </ActionIcon>
          <ActionIcon
            aria-label={t("kp.venue.redo")}
            disabled={!canRedo}
            onClick={onRedo}
            variant="default"
          >
            <IconArrowForwardUp size={16} />
          </ActionIcon>
        </Group>
      </Group>

      <Group align="flex-end" gap="sm" wrap="wrap">
        <Select
          allowDeselect={false}
          data={zones.map((zone) => ({ value: zone.id, label: zone.name }))}
          label={t("kp.venue.shape_zone")}
          onChange={onZoneChange}
          value={activeZoneId}
          w={220}
        />
        {selectedBoothNumber !== null ? (
          <NumberInput
            allowDecimal={false}
            label={t("kp.venue.booth_number")}
            min={1}
            onChange={(value) =>
              onBoothNumberChange(
                typeof value === "number" ? value : Number(value) || 0,
              )
            }
            value={selectedBoothNumber}
            w={140}
          />
        ) : null}
        <Button
          color="red"
          disabled={!canDeleteSelected}
          leftSection={<IconTrash size={16} />}
          onClick={onDeleteSelected}
          variant="light"
        >
          {t("kp.venue.delete_selected")}
        </Button>
      </Group>

      <Group gap="sm">
        <Button
          disabled={!canSave}
          leftSection={<IconDeviceFloppy size={16} />}
          loading={isSaving}
          onClick={onSave}
        >
          {t("kp.venue.save")}
        </Button>
        {isDirty ? (
          <Badge color="yellow" variant="light">
            {t("kp.venue.unsaved_changes")}
          </Badge>
        ) : null}
      </Group>
    </>
  );
};

export default VenueEditorToolbar;
