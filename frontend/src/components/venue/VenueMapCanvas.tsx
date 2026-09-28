import { ActionIcon, Group, Tooltip } from "@mantine/core";
import { IconMaximize, IconZoomIn, IconZoomOut } from "@tabler/icons-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import {
  shapeCentroid,
  shapeToPoints,
  type VenuePoint,
  type VenueShape,
} from "./venue-geometry";
import {
  identityVenueView,
  panVenueView,
  venueViewTransform,
  viewBoxToVenuePoint,
  zoomVenueView,
  ZOOM_STEP,
  type VenueView,
} from "./venue-view";

interface VenueCanvasZone {
  id: string;
  name: string;
  color: string;
  caption?: string;
  isFull?: boolean;
  descriptionId?: string;
}

export interface VenueCanvasShape {
  key: string;
  zoneId: string;
  shape: VenueShape;
  labelPosition: VenuePoint | null;
}

export interface VenueCanvasBooth {
  key: string;
  zoneId: string;
  boothNr: number;
  x: number;
  y: number;
  rotation: number | null;
  isHighlighted: boolean;
}

interface VenueMapCanvasProps {
  width: number;
  height: number;
  floorPlanUrl?: string | null;
  zones: VenueCanvasZone[];
  shapes: VenueCanvasShape[];
  booths: VenueCanvasBooth[];
  selectedZoneId?: string | null;
  selectedShapeKey?: string | null;
  selectedBoothKey?: string | null;
  panEnabled?: boolean;
  viewHeight?: number;
  underlay?: ReactNode;
  overlay?: ReactNode;
  onActivateShape?: (shape: VenueCanvasShape) => void;
  onActivateBooth?: (booth: VenueCanvasBooth) => void;
  onShapePointerDown?: (shape: VenueCanvasShape, point: VenuePoint) => void;
  onBoothPointerDown?: (booth: VenueCanvasBooth, point: VenuePoint) => void;
  onCanvasPointerDown?: (point: VenuePoint) => void;
  onCanvasPointerMove?: (point: VenuePoint) => void;
  onCanvasPointerUp?: (point: VenuePoint) => void;
  onCanvasDoubleClick?: (point: VenuePoint) => void;
}

const BOOTH_MARKER_SIZE = 18;
const FULL_HATCH_ID = "venue-full-hatch";

const capturePointer = (target: Element, pointerId: number) => {
  if (typeof target.setPointerCapture !== "function") return;
  target.setPointerCapture(pointerId);
};

const distanceBetween = (a: VenuePoint, b: VenuePoint) =>
  Math.hypot(a[0] - b[0], a[1] - b[1]);

const VenueMapCanvas = ({
  width,
  height,
  floorPlanUrl,
  zones,
  shapes,
  booths,
  selectedZoneId,
  selectedShapeKey,
  selectedBoothKey,
  panEnabled = true,
  viewHeight = 440,
  underlay,
  overlay,
  onActivateShape,
  onActivateBooth,
  onShapePointerDown,
  onBoothPointerDown,
  onCanvasPointerDown,
  onCanvasPointerMove,
  onCanvasPointerUp,
  onCanvasDoubleClick,
}: VenueMapCanvasProps) => {
  const { t } = useTranslation();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [view, setView] = useState<VenueView>(identityVenueView);
  const [hoveredShapeKey, setHoveredShapeKey] = useState<string | null>(null);
  const panRef = useRef<{ pointerId: number; last: VenuePoint } | null>(null);
  const pinchRef = useRef(new Map<number, VenuePoint>());
  const pinchDistanceRef = useRef<number | null>(null);

  const zoneById = useMemo(
    () => new Map(zones.map((zone) => [zone.id, zone])),
    [zones],
  );

  const toViewBoxPoint = useCallback(
    (clientX: number, clientY: number): VenuePoint => {
      const svg = svgRef.current;
      if (!svg) return [clientX, clientY];
      const rect = svg.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return [clientX, clientY];
      const scale = Math.min(rect.width / width, rect.height / height);
      return [
        (clientX - rect.left - (rect.width - width * scale) / 2) / scale,
        (clientY - rect.top - (rect.height - height * scale) / 2) / scale,
      ];
    },
    [width, height],
  );

  const toVenuePoint = useCallback(
    (clientX: number, clientY: number) =>
      viewBoxToVenuePoint(view, toViewBoxPoint(clientX, clientY)),
    [toViewBoxPoint, view],
  );

  const zoomAroundCenter = (factor: number) =>
    setView((current) =>
      zoomVenueView(current, factor, [width / 2, height / 2]),
    );

  const handleCanvasKeyDown = (event: ReactKeyboardEvent<SVGSVGElement>) => {
    if (event.key === "+" || event.key === "=") {
      event.preventDefault();
      zoomAroundCenter(ZOOM_STEP);
      return;
    }
    if (event.key === "-" || event.key === "_") {
      event.preventDefault();
      zoomAroundCenter(1 / ZOOM_STEP);
      return;
    }
    if (event.key !== "0") return;
    event.preventDefault();
    setView(identityVenueView);
  };

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      const focus = toViewBoxPoint(event.clientX, event.clientY);
      const factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
      setView((current) => zoomVenueView(current, factor, focus));
    };
    svg.addEventListener("wheel", handleWheel, { passive: false });
    return () => svg.removeEventListener("wheel", handleWheel);
  }, [toViewBoxPoint]);

  const handlePointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    const viewBoxPoint = toViewBoxPoint(event.clientX, event.clientY);
    pinchRef.current.set(event.pointerId, viewBoxPoint);
    if (pinchRef.current.size === 2) {
      const [first, second] = [...pinchRef.current.values()];
      pinchDistanceRef.current = distanceBetween(first, second);
      panRef.current = null;
      return;
    }
    onCanvasPointerDown?.(viewBoxToVenuePoint(view, viewBoxPoint));
    if (!panEnabled) return;
    panRef.current = { pointerId: event.pointerId, last: viewBoxPoint };
    capturePointer(event.currentTarget, event.pointerId);
  };

  const handlePointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    const viewBoxPoint = toViewBoxPoint(event.clientX, event.clientY);
    if (pinchRef.current.has(event.pointerId)) {
      pinchRef.current.set(event.pointerId, viewBoxPoint);
    }
    if (pinchRef.current.size === 2) {
      const [first, second] = [...pinchRef.current.values()];
      const distance = distanceBetween(first, second);
      const previous = pinchDistanceRef.current;
      pinchDistanceRef.current = distance;
      if (previous !== null && previous > 0 && distance > 0) {
        const focus: VenuePoint = [
          (first[0] + second[0]) / 2,
          (first[1] + second[1]) / 2,
        ];
        setView((current) =>
          zoomVenueView(current, distance / previous, focus),
        );
      }
      return;
    }
    const pan = panRef.current;
    if (pan !== null && pan.pointerId === event.pointerId) {
      const deltaX = viewBoxPoint[0] - pan.last[0];
      const deltaY = viewBoxPoint[1] - pan.last[1];
      pan.last = viewBoxPoint;
      setView((current) => panVenueView(current, deltaX, deltaY));
      return;
    }
    onCanvasPointerMove?.(viewBoxToVenuePoint(view, viewBoxPoint));
  };

  const handlePointerUp = (event: ReactPointerEvent<SVGSVGElement>) => {
    pinchRef.current.delete(event.pointerId);
    if (pinchRef.current.size < 2) pinchDistanceRef.current = null;
    if (panRef.current?.pointerId === event.pointerId) panRef.current = null;
    onCanvasPointerUp?.(toVenuePoint(event.clientX, event.clientY));
  };

  const shapeOpacity = (shape: VenueCanvasShape) => {
    const isActive =
      selectedShapeKey === shape.key ||
      selectedZoneId === shape.zoneId ||
      hoveredShapeKey === shape.key;
    return isActive ? 0.85 : 0.35;
  };

  const shapeStyle = (shape: VenueCanvasShape, color: string) => ({
    fill: color,
    fillOpacity: shapeOpacity(shape),
    stroke: color,
    strokeWidth: 2 / view.scale,
  });

  const hatchStyle = {
    fill: `url(#${FULL_HATCH_ID})`,
    stroke: "none",
    "data-full-hatch": true,
  };

  const renderShapeBody = (
    shape: VenueCanvasShape,
    common: ReturnType<typeof shapeStyle> | typeof hatchStyle,
  ) => {
    if (shape.shape.type === "rect") {
      return (
        <rect
          x={shape.shape.x}
          y={shape.shape.y}
          width={shape.shape.w}
          height={shape.shape.h}
          rx={4}
          {...common}
        />
      );
    }
    return (
      <polygon
        points={shapeToPoints(shape.shape)
          .map(([x, y]) => `${x},${y}`)
          .join(" ")}
        {...common}
      />
    );
  };

  const fontSize = 16 / view.scale;

  return (
    <div style={{ position: "relative" }}>
      <Group
        gap={4}
        style={{ position: "absolute", top: 8, right: 8, zIndex: 2 }}
      >
        <Tooltip label={t("kp.venue.zoom_in")}>
          <ActionIcon
            aria-label={t("kp.venue.zoom_in")}
            onClick={() => zoomAroundCenter(ZOOM_STEP)}
            variant="default"
          >
            <IconZoomIn size={16} />
          </ActionIcon>
        </Tooltip>
        <Tooltip label={t("kp.venue.zoom_out")}>
          <ActionIcon
            aria-label={t("kp.venue.zoom_out")}
            onClick={() => zoomAroundCenter(1 / ZOOM_STEP)}
            variant="default"
          >
            <IconZoomOut size={16} />
          </ActionIcon>
        </Tooltip>
        <Tooltip label={t("kp.venue.zoom_fit")}>
          <ActionIcon
            aria-label={t("kp.venue.zoom_fit")}
            onClick={() => setView(identityVenueView)}
            variant="default"
          >
            <IconMaximize size={16} />
          </ActionIcon>
        </Tooltip>
      </Group>
      <svg
        ref={svgRef}
        role="group"
        aria-label={t("kp.venue.map_label")}
        aria-keyshortcuts="Plus Minus 0"
        tabIndex={0}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        onKeyDown={handleCanvasKeyDown}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onDoubleClick={(event) =>
          onCanvasDoubleClick?.(toVenuePoint(event.clientX, event.clientY))
        }
        style={{
          width: "100%",
          height: viewHeight,
          display: "block",
          touchAction: "none",
          backgroundColor: "var(--mantine-color-body)",
          color: floorPlanUrl
            ? "var(--mantine-color-black)"
            : "var(--mantine-color-text)",
          borderRadius: "var(--mantine-radius-md)",
          cursor: panEnabled ? "grab" : "crosshair",
        }}
      >
        <defs>
          <pattern
            id={FULL_HATCH_ID}
            width={12}
            height={12}
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <line
              x1={0}
              y1={0}
              x2={0}
              y2={12}
              stroke="var(--mantine-color-black)"
              strokeOpacity={0.45}
              strokeWidth={3}
            />
          </pattern>
        </defs>
        <g transform={venueViewTransform(view)}>
          {floorPlanUrl ? (
            <image
              href={floorPlanUrl}
              x={0}
              y={0}
              width={width}
              height={height}
              preserveAspectRatio="none"
            />
          ) : null}
          {underlay}
          <rect
            x={0}
            y={0}
            width={width}
            height={height}
            fill="none"
            stroke="var(--mantine-color-dimmed)"
            strokeWidth={1 / view.scale}
          />
          {shapes.map((shape) => {
            const zone = zoneById.get(shape.zoneId);
            const color = zone?.color ?? "var(--mantine-color-gray-5)";
            const [labelX, labelY] =
              shape.labelPosition ?? shapeCentroid(shape.shape);
            const zoneName = zone?.name ?? t("kp.venue.shape_unassigned");
            return (
              <g
                key={shape.key}
                role="button"
                tabIndex={0}
                aria-label={zoneName}
                aria-describedby={zone?.descriptionId}
                aria-pressed={
                  selectedShapeKey === shape.key ||
                  selectedZoneId === shape.zoneId
                }
                onClick={() => onActivateShape?.(shape)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" && event.key !== " ") return;
                  event.preventDefault();
                  onActivateShape?.(shape);
                }}
                onPointerDown={(event) => {
                  if (!onShapePointerDown) return;
                  event.stopPropagation();
                  onShapePointerDown(
                    shape,
                    toVenuePoint(event.clientX, event.clientY),
                  );
                }}
                onMouseEnter={() => setHoveredShapeKey(shape.key)}
                onMouseLeave={() => setHoveredShapeKey(null)}
                style={{ cursor: "pointer" }}
              >
                <title>
                  {zone?.caption ? `${zoneName} · ${zone.caption}` : zoneName}
                </title>
                {renderShapeBody(shape, shapeStyle(shape, color))}
                {zone?.isFull ? renderShapeBody(shape, hatchStyle) : null}
                {floorPlanUrl ? null : (
                  <>
                    <text
                      x={labelX}
                      y={labelY}
                      textAnchor="middle"
                      fontSize={fontSize}
                      fontWeight={600}
                      fill="currentColor"
                      style={{ pointerEvents: "none", userSelect: "none" }}
                    >
                      {zoneName}
                    </text>
                    <text
                      x={labelX}
                      y={labelY + fontSize * 1.2}
                      textAnchor="middle"
                      fontSize={fontSize * 0.8}
                      fill="currentColor"
                      style={{ pointerEvents: "none", userSelect: "none" }}
                    >
                      {zone?.caption ?? ""}
                    </text>
                  </>
                )}
              </g>
            );
          })}
          {booths.map((booth) => {
            const zone = zoneById.get(booth.zoneId);
            const isSelected = selectedBoothKey === booth.key;
            const boothZoneName = zone?.name ?? t("kp.venue.shape_unassigned");
            return (
              <g
                key={booth.key}
                role={onActivateBooth ? "button" : "img"}
                tabIndex={onActivateBooth ? 0 : undefined}
                aria-label={`${t("kp.venue.booth_marker")} ${booth.boothNr} ${boothZoneName}`}
                aria-describedby={zone?.descriptionId}
                aria-pressed={onActivateBooth ? isSelected : undefined}
                transform={`translate(${booth.x} ${booth.y}) rotate(${booth.rotation ?? 0})`}
                onClick={() => onActivateBooth?.(booth)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" && event.key !== " ") return;
                  event.preventDefault();
                  onActivateBooth?.(booth);
                }}
                onPointerDown={(event) => {
                  if (!onBoothPointerDown) return;
                  event.stopPropagation();
                  onBoothPointerDown(
                    booth,
                    toVenuePoint(event.clientX, event.clientY),
                  );
                }}
                style={{ cursor: onActivateBooth ? "pointer" : "default" }}
              >
                <rect
                  x={-BOOTH_MARKER_SIZE / 2}
                  y={-BOOTH_MARKER_SIZE / 2}
                  width={BOOTH_MARKER_SIZE}
                  height={BOOTH_MARKER_SIZE}
                  rx={3}
                  fill={
                    booth.isHighlighted
                      ? "var(--mantine-primary-color-filled)"
                      : "var(--mantine-color-body)"
                  }
                  stroke={
                    isSelected
                      ? "var(--mantine-primary-color-filled)"
                      : (zone?.color ?? "var(--mantine-color-gray-6)")
                  }
                  strokeWidth={
                    (isSelected || booth.isHighlighted ? 3 : 1.5) / view.scale
                  }
                />
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={BOOTH_MARKER_SIZE * 0.6}
                  fill={
                    booth.isHighlighted
                      ? "var(--mantine-color-white)"
                      : "currentColor"
                  }
                  style={{ pointerEvents: "none", userSelect: "none" }}
                >
                  {booth.boothNr}
                </text>
              </g>
            );
          })}
          {overlay}
        </g>
      </svg>
    </div>
  );
};

export default VenueMapCanvas;
