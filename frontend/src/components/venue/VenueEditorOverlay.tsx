import type { PointerEvent } from "react";
import { rectFromPoints, type VenuePoint } from "./venue-geometry";

export interface DragRect {
  start: VenuePoint;
  current: VenuePoint;
}

interface VenueEditorOverlayProps {
  dragRect: DragRect | null;
  pendingPolygon: VenuePoint[];
  labelAnchor: VenuePoint | null;
  onLabelPointerDown: (event: PointerEvent<SVGCircleElement>) => void;
}

export const VenueEditorOverlay = ({
  dragRect,
  pendingPolygon,
  labelAnchor,
  onLabelPointerDown,
}: VenueEditorOverlayProps) => (
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
    {labelAnchor !== null ? (
      <circle
        cx={labelAnchor[0]}
        cy={labelAnchor[1]}
        fill="var(--mantine-primary-color-filled)"
        onPointerDown={onLabelPointerDown}
        r={7}
        style={{ cursor: "move" }}
      />
    ) : null}
  </>
);

interface VenueGridUnderlayProps {
  gridId: string;
  gridSize: number;
  width: number;
  height: number;
}

export const VenueGridUnderlay = ({
  gridId,
  gridSize,
  width,
  height,
}: VenueGridUnderlayProps) => (
  <>
    <defs>
      <pattern
        height={gridSize}
        id={gridId}
        patternUnits="userSpaceOnUse"
        width={gridSize}
      >
        <path
          d={`M ${gridSize} 0 L 0 0 0 ${gridSize}`}
          fill="none"
          stroke="var(--mantine-color-dimmed)"
          strokeWidth={0.5}
        />
      </pattern>
    </defs>
    <rect
      fill={`url(#${gridId})`}
      height={height}
      opacity={0.25}
      width={width}
      x={0}
      y={0}
    />
  </>
);
