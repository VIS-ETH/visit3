import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Group,
  NumberInput,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconArrowBackUp,
  IconArrowForwardUp,
  IconDeviceFloppy,
  IconTrash,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import type {
  BoothZoneResponse,
  VenueLayoutResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  getGetEventVenueQueryKey,
  getListVenueLayoutsQueryKey,
  useReplaceVenueBooths,
  useReplaceVenueZoneShapes,
} from "../../orval/generated/kp/kp";
import VenueMapCanvas, {
  type VenueCanvasBooth,
  type VenueCanvasShape,
} from "./VenueMapCanvas";
import {
  boothsRequest,
  commitDraft,
  createDraftHistory,
  draftFromLayout,
  isSameDraft,
  nextBoothNumber,
  nextDraftKey,
  redoDraft,
  shapesRequest,
  undoDraft,
  type VenueDraft,
  type VenueDraftHistory,
} from "./venue-draft";
import {
  countOutsideBounds,
  MAX_LAYOUT_BOOTHS,
  MAX_LAYOUT_SHAPES,
  MAX_POLYGON_POINTS,
} from "./venue-limits";
import {
  clampPointToBounds,
  rectFromPoints,
  shapeCentroid,
  snapPoint,
  snapValue,
  translateShapeInsideBounds,
  type VenuePoint,
  type VenueShape,
} from "./venue-geometry";

const GRID_SIZE = 10;

type VenueTool = "select" | "rect" | "polygon" | "booth";

interface MoveState {
  kind: "shape" | "label" | "booth";
  key: string;
  start: VenuePoint;
  origin: VenuePoint;
  shape: VenueShape | null;
  base: VenueDraftHistory;
}

interface VenueLayoutEditorProps {
  layout: VenueLayoutResponse;
  zones: BoothZoneResponse[];
  onDirtyChange?: (isDirty: boolean) => void;
}

const isTextEntryFocused = () => {
  const active = document.activeElement;
  if (!(active instanceof HTMLElement)) return false;
  return (
    active.tagName === "INPUT" ||
    active.tagName === "TEXTAREA" ||
    active.isContentEditable
  );
};

const VenueLayoutEditor = ({
  layout,
  zones,
  onDirtyChange,
}: VenueLayoutEditorProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [history, setHistory] = useState<VenueDraftHistory>(() =>
    createDraftHistory(draftFromLayout(layout)),
  );
  const [savedDraft, setSavedDraft] = useState<VenueDraft>(() =>
    draftFromLayout(layout),
  );
  const [saveErrorCode, setSaveErrorCode] = useState<string | null>(null);
  const [tool, setTool] = useState<VenueTool>("select");
  const [selectedShapeKey, setSelectedShapeKey] = useState<string | null>(null);
  const [selectedBoothKey, setSelectedBoothKey] = useState<string | null>(null);
  const [pickedZoneId, setPickedZoneId] = useState<string | null>(null);
  const [isSnapEnabled, setIsSnapEnabled] = useState(true);
  const [pendingPolygon, setPendingPolygon] = useState<VenuePoint[]>([]);
  const [dragRect, setDragRect] = useState<{
    start: VenuePoint;
    current: VenuePoint;
  } | null>(null);
  const moveRef = useRef<MoveState | null>(null);

  const draft = history.present;
  const selectedShape =
    draft.shapes.find((shape) => shape.key === selectedShapeKey) ?? null;
  const selectedBooth =
    draft.booths.find((booth) => booth.key === selectedBoothKey) ?? null;
  const activeZoneId =
    selectedShape?.zoneId ??
    selectedBooth?.zoneId ??
    pickedZoneId ??
    zones.at(0)?.id ??
    null;

  const selectShape = (key: string | null) => {
    setSelectedShapeKey(key);
    setSelectedBoothKey(null);
  };

  const selectBooth = (key: string | null) => {
    setSelectedBoothKey(key);
    setSelectedShapeKey(null);
  };

  const commit = (present: VenueDraft) =>
    setHistory((current) => commitDraft(current, present));

  const normalise = useCallback(
    (point: VenuePoint): VenuePoint => {
      const clamped = clampPointToBounds(point, layout.width, layout.height);
      return isSnapEnabled ? snapPoint(clamped, GRID_SIZE) : clamped;
    },
    [isSnapEnabled, layout.width, layout.height],
  );

  const hasShapeCapacity = draft.shapes.length < MAX_LAYOUT_SHAPES;
  const hasBoothCapacity = draft.booths.length < MAX_LAYOUT_BOOTHS;
  const hasPolygonPointCapacity = pendingPolygon.length < MAX_POLYGON_POINTS;
  const outsideBoundsCount = countOutsideBounds(draft, layout);

  const closePolygon = () => {
    if (pendingPolygon.length < 3 || activeZoneId === null) {
      setPendingPolygon([]);
      return;
    }
    if (!hasShapeCapacity) {
      setPendingPolygon([]);
      return;
    }
    const key = nextDraftKey();
    commit({
      ...draft,
      shapes: [
        ...draft.shapes,
        {
          key,
          zoneId: activeZoneId,
          shape: { type: "polygon", points: pendingPolygon },
          labelPosition: null,
        },
      ],
    });
    setPendingPolygon([]);
    selectShape(key);
  };

  const deleteSelected = () => {
    if (selectedShapeKey !== null) {
      commit({
        ...draft,
        shapes: draft.shapes.filter((shape) => shape.key !== selectedShapeKey),
      });
      setSelectedShapeKey(null);
      return;
    }
    if (selectedBoothKey === null) return;
    commit({
      ...draft,
      booths: draft.booths.filter((booth) => booth.key !== selectedBoothKey),
    });
    setSelectedBoothKey(null);
  };

  const shortcutsRef = useRef({
    closePolygon,
    deleteSelected,
    hasPendingPolygon: pendingPolygon.length > 0,
  });

  useEffect(() => {
    shortcutsRef.current = {
      closePolygon,
      deleteSelected,
      hasPendingPolygon: pendingPolygon.length > 0,
    };
  });

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const shortcuts = shortcutsRef.current;
      if (event.key === "Escape") {
        setPendingPolygon([]);
        setDragRect(null);
        return;
      }
      if (event.key === "Enter" && shortcuts.hasPendingPolygon) {
        event.preventDefault();
        shortcuts.closePolygon();
        return;
      }
      if (event.key !== "Delete" && event.key !== "Backspace") return;
      if (isTextEntryFocused()) return;
      shortcuts.deleteSelected();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const applyMove = (move: MoveState, point: VenuePoint) => {
    const rawDeltaX = point[0] - move.start[0];
    const rawDeltaY = point[1] - move.start[1];
    const deltaX = isSnapEnabled ? snapValue(rawDeltaX, GRID_SIZE) : rawDeltaX;
    const deltaY = isSnapEnabled ? snapValue(rawDeltaY, GRID_SIZE) : rawDeltaY;
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
                    layout.width,
                    layout.height,
                  ),
                };
              }
              return { ...shape, labelPosition: moved };
            }),
          };
    setHistory({
      past: [...move.base.past, base],
      present,
      future: [],
    });
  };

  const handleCanvasPointerDown = (point: VenuePoint) => {
    const target = normalise(point);
    if (tool === "rect") {
      if (!hasShapeCapacity) return;
      setDragRect({ start: target, current: target });
      return;
    }
    if (tool === "polygon") {
      if (!hasShapeCapacity || !hasPolygonPointCapacity) return;
      setPendingPolygon((points) => [...points, target]);
      return;
    }
    if (tool === "booth") {
      if (activeZoneId === null || !hasBoothCapacity) return;
      const key = nextDraftKey();
      commit({
        ...draft,
        booths: [
          ...draft.booths,
          {
            key,
            zoneId: activeZoneId,
            boothNr: nextBoothNumber(draft.booths),
            x: target[0],
            y: target[1],
            rotation: null,
          },
        ],
      });
      selectBooth(key);
      return;
    }
    selectShape(null);
  };

  const handleCanvasPointerMove = (point: VenuePoint) => {
    if (dragRect !== null) {
      setDragRect({ start: dragRect.start, current: normalise(point) });
      return;
    }
    const move = moveRef.current;
    if (move !== null) applyMove(move, point);
  };

  const handleCanvasPointerUp = () => {
    moveRef.current = null;
    if (dragRect === null) return;
    setDragRect(null);
    const rect = rectFromPoints(dragRect.start, dragRect.current);
    if (rect.w < GRID_SIZE || rect.h < GRID_SIZE || activeZoneId === null) {
      return;
    }
    const key = nextDraftKey();
    commit({
      ...draft,
      shapes: [
        ...draft.shapes,
        { key, zoneId: activeZoneId, shape: rect, labelPosition: null },
      ],
    });
    selectShape(key);
  };

  const handleShapePointerDown = (
    shape: VenueCanvasShape,
    point: VenuePoint,
  ) => {
    if (tool !== "select") return;
    selectShape(shape.key);
    const draftShape = draft.shapes.find(
      (candidate) => candidate.key === shape.key,
    );
    if (draftShape === undefined) return;
    moveRef.current = {
      kind: "shape",
      key: shape.key,
      start: point,
      origin: [0, 0],
      shape: draftShape.shape,
      base: history,
    };
  };

  const handleBoothPointerDown = (
    booth: VenueCanvasBooth,
    point: VenuePoint,
  ) => {
    if (tool !== "select") return;
    selectBooth(booth.key);
    moveRef.current = {
      kind: "booth",
      key: booth.key,
      start: point,
      origin: [booth.x, booth.y],
      shape: null,
      base: history,
    };
  };

  const changeBoothNumber = (boothNr: number) => {
    if (selectedBooth === null || boothNr < 1) return;
    commit({
      ...draft,
      booths: draft.booths.map((booth) =>
        booth.key === selectedBooth.key ? { ...booth, boothNr } : booth,
      ),
    });
  };

  const handleZoneChange = (value: string | null) => {
    if (value === null) return;
    setPickedZoneId(value);
    if (selectedBooth !== null) {
      commit({
        ...draft,
        booths: draft.booths.map((booth) =>
          booth.key === selectedBooth.key ? { ...booth, zoneId: value } : booth,
        ),
      });
      return;
    }
    if (selectedShape === null) return;
    commit({
      ...draft,
      shapes: draft.shapes.map((shape) =>
        shape.key === selectedShape.key ? { ...shape, zoneId: value } : shape,
      ),
    });
  };

  const canvasZones = zones.map((zone) => ({
    id: zone.id,
    name: zone.name,
    color: zone.color,
  }));

  const canvasBooths = draft.booths.map((booth) => ({
    ...booth,
    isHighlighted: false,
  }));

  const isDirty = !isSameDraft(draft, savedDraft);

  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  useEffect(() => {
    if (!isDirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  const { mutateAsync: replaceShapes, isPending: isSavingShapes } =
    useReplaceVenueZoneShapes();
  const { mutateAsync: replaceBooths, isPending: isSavingBooths } =
    useReplaceVenueBooths();

  const save = async () => {
    setSaveErrorCode(null);
    try {
      await replaceShapes({
        layoutId: layout.id,
        data: shapesRequest(draft),
      });
      const saved = await replaceBooths({
        layoutId: layout.id,
        data: boothsRequest(draft),
      });
      setSavedDraft(draftFromLayout(saved));
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: getListVenueLayoutsQueryKey(layout.event_id),
        }),
        queryClient.invalidateQueries({
          queryKey: getGetEventVenueQueryKey(layout.event_id),
        }),
      ]);
      notifications.show({ color: "green", message: t("kp.venue.saved") });
    } catch (error) {
      setSaveErrorCode(getApiErrorCode(error) ?? "error.internal");
    }
  };

  const labelAnchor =
    selectedShape === null
      ? null
      : (selectedShape.labelPosition ?? shapeCentroid(selectedShape.shape));

  const gridId = `venue-grid-${layout.id}`;

  const overlay = (
    <>
      {dragRect !== null ? (
        <rect
          {...rectFromPoints(dragRect.start, dragRect.current)}
          fill="var(--mantine-primary-color-filled)"
          fillOpacity={0.2}
          stroke="var(--mantine-primary-color-filled)"
          strokeDasharray="6 4"
          strokeWidth={2}
        />
      ) : null}
      {pendingPolygon.length > 0 ? (
        <g>
          <polyline
            fill="none"
            points={pendingPolygon.map(([x, y]) => `${x},${y}`).join(" ")}
            stroke="var(--mantine-primary-color-filled)"
            strokeDasharray="6 4"
            strokeWidth={2}
          />
          {pendingPolygon.map(([x, y]) => (
            <circle
              cx={x}
              cy={y}
              fill="var(--mantine-primary-color-filled)"
              key={`${x}-${y}`}
              r={5}
            />
          ))}
        </g>
      ) : null}
      {labelAnchor !== null && selectedShape !== null ? (
        <circle
          cx={labelAnchor[0]}
          cy={labelAnchor[1]}
          fill="var(--mantine-primary-color-filled)"
          onPointerDown={(event) => {
            event.stopPropagation();
            moveRef.current = {
              kind: "label",
              key: selectedShape.key,
              start: [labelAnchor[0], labelAnchor[1]],
              origin: [labelAnchor[0], labelAnchor[1]],
              shape: selectedShape.shape,
              base: history,
            };
          }}
          r={7}
          style={{ cursor: "move" }}
        />
      ) : null}
    </>
  );

  const underlay = isSnapEnabled ? (
    <>
      <defs>
        <pattern
          height={GRID_SIZE}
          id={gridId}
          patternUnits="userSpaceOnUse"
          width={GRID_SIZE}
        >
          <path
            d={`M ${GRID_SIZE} 0 L 0 0 0 ${GRID_SIZE}`}
            fill="none"
            stroke="var(--mantine-color-dimmed)"
            strokeWidth={0.5}
          />
        </pattern>
      </defs>
      <rect
        fill={`url(#${gridId})`}
        height={layout.height}
        opacity={0.25}
        width={layout.width}
        x={0}
        y={0}
      />
    </>
  ) : null;

  return (
    <Stack gap="sm">
      <Group justify="space-between" wrap="wrap">
        <SegmentedControl
          data={[
            { value: "select", label: t("kp.venue.tool_select") },
            { value: "rect", label: t("kp.venue.tool_rect") },
            { value: "polygon", label: t("kp.venue.tool_polygon") },
            { value: "booth", label: t("kp.venue.tool_booth") },
          ]}
          onChange={(value) => {
            setTool(value as VenueTool);
            setPendingPolygon([]);
            setDragRect(null);
          }}
          value={tool}
        />
        <Group gap="xs">
          <Switch
            checked={isSnapEnabled}
            label={t("kp.venue.snap_grid")}
            onChange={(event) => setIsSnapEnabled(event.currentTarget.checked)}
          />
          <ActionIcon
            aria-label={t("kp.venue.undo")}
            disabled={history.past.length === 0}
            onClick={() => setHistory(undoDraft)}
            variant="default"
          >
            <IconArrowBackUp size={16} />
          </ActionIcon>
          <ActionIcon
            aria-label={t("kp.venue.redo")}
            disabled={history.future.length === 0}
            onClick={() => setHistory(redoDraft)}
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
          onChange={handleZoneChange}
          value={activeZoneId}
          w={220}
        />
        {selectedBooth !== null ? (
          <NumberInput
            allowDecimal={false}
            label={t("kp.venue.booth_number")}
            min={1}
            onChange={(value) =>
              changeBoothNumber(
                typeof value === "number" ? value : Number(value) || 0,
              )
            }
            value={selectedBooth.boothNr}
            w={140}
          />
        ) : null}
        <Button
          color="red"
          disabled={selectedShape === null && selectedBooth === null}
          leftSection={<IconTrash size={16} />}
          onClick={deleteSelected}
          variant="light"
        >
          {t("kp.venue.delete_selected")}
        </Button>
      </Group>

      <Group gap="sm">
        <Button
          disabled={outsideBoundsCount > 0}
          leftSection={<IconDeviceFloppy size={16} />}
          loading={isSavingShapes || isSavingBooths}
          onClick={() => {
            void save();
          }}
        >
          {t("kp.venue.save")}
        </Button>
        {isDirty ? (
          <Badge color="yellow" variant="light">
            {t("kp.venue.unsaved_changes")}
          </Badge>
        ) : null}
      </Group>

      {outsideBoundsCount > 0 ? (
        <Alert color="red" icon={<IconAlertCircle />}>
          {t("kp.venue.outside_layout_hint", {
            count: outsideBoundsCount,
            width: layout.width,
            height: layout.height,
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
        {tool === "polygon"
          ? t("kp.venue.polygon_hint")
          : tool === "rect"
            ? t("kp.venue.rect_hint")
            : tool === "booth"
              ? t("kp.venue.booth_hint")
              : t("kp.venue.select_hint")}
      </Text>

      <Paper withBorder radius="md" p="xs">
        <VenueMapCanvas
          backgroundUrl={layout.background_url}
          booths={canvasBooths}
          height={layout.height}
          onActivateBooth={(booth) => selectBooth(booth.key)}
          onActivateShape={(shape) => selectShape(shape.key)}
          onCanvasDoubleClick={closePolygon}
          onCanvasPointerDown={handleCanvasPointerDown}
          onCanvasPointerMove={handleCanvasPointerMove}
          onCanvasPointerUp={handleCanvasPointerUp}
          onBoothPointerDown={handleBoothPointerDown}
          onShapePointerDown={handleShapePointerDown}
          overlay={overlay}
          panEnabled={tool === "select"}
          selectedBoothKey={selectedBoothKey}
          selectedShapeKey={selectedShapeKey}
          shapes={draft.shapes}
          underlay={underlay}
          width={layout.width}
          zones={canvasZones}
        />
      </Paper>
    </Stack>
  );
};

export default VenueLayoutEditor;
