import { Paper, Stack } from "@mantine/core";
import { useCallback, useRef, useState } from "react";
import type {
  BoothZoneResponse,
  VenueLayoutResponse,
} from "../../orval/generated/fastAPI.schemas";
import VenueMapCanvas, {
  type VenueCanvasBooth,
  type VenueCanvasShape,
} from "./VenueMapCanvas";
import VenueEditorNotices from "./VenueEditorNotices";
import {
  VenueEditorOverlay,
  VenueGridUnderlay,
  type DragRect,
} from "./VenueEditorOverlay";
import VenueEditorToolbar, { type VenueTool } from "./VenueEditorToolbar";
import {
  commitDraft,
  createDraftHistory,
  draftFromLayout,
  nextBoothNumber,
  nextDraftKey,
  redoDraft,
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
  type VenuePoint,
} from "./venue-geometry";
import { floorPlanImage } from "./floor-plans";
import { useVenueLayoutSave } from "./use-venue-layout-save";
import { useVenueShortcuts } from "./use-venue-shortcuts";
import { movedHistory, type VenueMove } from "./venue-move";

const GRID_SIZE = 10;

interface VenueLayoutEditorProps {
  layout: VenueLayoutResponse;
  zones: BoothZoneResponse[];
  onDirtyChange?: (isDirty: boolean) => void;
}

const VenueLayoutEditor = ({
  layout,
  zones,
  onDirtyChange,
}: VenueLayoutEditorProps) => {
  const [history, setHistory] = useState<VenueDraftHistory>(() =>
    createDraftHistory(draftFromLayout(layout)),
  );
  const [tool, setTool] = useState<VenueTool>("select");
  const [selectedShapeKey, setSelectedShapeKey] = useState<string | null>(null);
  const [selectedBoothKey, setSelectedBoothKey] = useState<string | null>(null);
  const [pickedZoneId, setPickedZoneId] = useState<string | null>(null);
  const [isSnapEnabled, setIsSnapEnabled] = useState(true);
  const [pendingPolygon, setPendingPolygon] = useState<VenuePoint[]>([]);
  const [dragRect, setDragRect] = useState<DragRect | null>(null);
  const moveRef = useRef<VenueMove | null>(null);

  const draft = history.present;
  const { save, isSaving, isDirty, saveErrorCode } = useVenueLayoutSave(
    layout,
    draft,
    onDirtyChange,
  );
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

  useVenueShortcuts({
    cancelDrawing: () => {
      setPendingPolygon([]);
      setDragRect(null);
    },
    closePolygon,
    deleteSelected,
    hasPendingPolygon: pendingPolygon.length > 0,
  });

  const applyMove = (move: VenueMove, point: VenuePoint) =>
    setHistory(
      movedHistory(move, point, {
        gridSize: isSnapEnabled ? GRID_SIZE : null,
        width: layout.width,
        height: layout.height,
        normalise,
      }),
    );

  const handleCanvasPointerDown = (
    point: VenuePoint,
    boothZoneId: string | null = activeZoneId,
  ) => {
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
      if (boothZoneId === null || !hasBoothCapacity) return;
      const key = nextDraftKey();
      commit({
        ...draft,
        booths: [
          ...draft.booths,
          {
            key,
            zoneId: boothZoneId,
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
    if (tool !== "select") {
      handleCanvasPointerDown(point, shape.zoneId);
      return;
    }
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

  const labelAnchor =
    selectedShape === null
      ? null
      : (selectedShape.labelPosition ?? shapeCentroid(selectedShape.shape));

  const startLabelMove = () => {
    if (labelAnchor === null || selectedShape === null) return;
    moveRef.current = {
      kind: "label",
      key: selectedShape.key,
      start: [labelAnchor[0], labelAnchor[1]],
      origin: [labelAnchor[0], labelAnchor[1]],
      shape: selectedShape.shape,
      base: history,
    };
  };

  return (
    <Stack gap="sm">
      <VenueEditorToolbar
        activeZoneId={activeZoneId}
        canDeleteSelected={selectedShape !== null || selectedBooth !== null}
        canRedo={history.future.length > 0}
        canSave={outsideBoundsCount === 0}
        canUndo={history.past.length > 0}
        isDirty={isDirty}
        isSaving={isSaving}
        isSnapEnabled={isSnapEnabled}
        onBoothNumberChange={changeBoothNumber}
        onDeleteSelected={deleteSelected}
        onRedo={() => setHistory(redoDraft)}
        onSave={() => void save()}
        onSnapChange={setIsSnapEnabled}
        onToolChange={(value) => {
          setTool(value);
          setPendingPolygon([]);
          setDragRect(null);
        }}
        onUndo={() => setHistory(undoDraft)}
        onZoneChange={handleZoneChange}
        selectedBoothNumber={selectedBooth?.boothNr ?? null}
        tool={tool}
        zones={zones}
      />

      <VenueEditorNotices
        hasBoothCapacity={hasBoothCapacity}
        hasPolygonPointCapacity={hasPolygonPointCapacity}
        hasShapeCapacity={hasShapeCapacity}
        layoutHeight={layout.height}
        layoutWidth={layout.width}
        outsideBoundsCount={outsideBoundsCount}
        saveErrorCode={saveErrorCode}
        tool={tool}
      />

      <Paper withBorder radius="md" p="xs">
        <VenueMapCanvas
          floorPlanUrl={floorPlanImage(layout.floor_plan)}
          booths={canvasBooths}
          height={layout.height}
          onActivateBooth={(booth) => selectBooth(booth.key)}
          onActivateShape={(shape) => {
            if (tool === "select") selectShape(shape.key);
          }}
          onCanvasDoubleClick={closePolygon}
          onCanvasPointerDown={handleCanvasPointerDown}
          onCanvasPointerMove={handleCanvasPointerMove}
          onCanvasPointerUp={handleCanvasPointerUp}
          onBoothPointerDown={handleBoothPointerDown}
          onShapePointerDown={handleShapePointerDown}
          overlay={
            <VenueEditorOverlay
              dragRect={dragRect}
              labelAnchor={selectedShape === null ? null : labelAnchor}
              onLabelPointerDown={(event) => {
                event.stopPropagation();
                startLabelMove();
              }}
              pendingPolygon={pendingPolygon}
            />
          }
          panEnabled={tool === "select"}
          selectedBoothKey={selectedBoothKey}
          selectedShapeKey={selectedShapeKey}
          shapes={draft.shapes}
          underlay={
            isSnapEnabled ? (
              <VenueGridUnderlay
                gridId={`venue-grid-${layout.id}`}
                gridSize={GRID_SIZE}
                height={layout.height}
                width={layout.width}
              />
            ) : null
          }
          width={layout.width}
          zones={canvasZones}
        />
      </Paper>
    </Stack>
  );
};

export default VenueLayoutEditor;
