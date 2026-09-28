import type {
  VenuePolygonShape,
  VenueRectShape,
} from "../../orval/generated/fastAPI.schemas";

export type VenueShape = VenuePolygonShape | VenueRectShape;

export type VenuePoint = [number, number];

interface VenueBounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

export const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

export const rectToPoints = (rect: VenueRectShape): VenuePoint[] => [
  [rect.x, rect.y],
  [rect.x + rect.w, rect.y],
  [rect.x + rect.w, rect.y + rect.h],
  [rect.x, rect.y + rect.h],
];

export const shapeToPoints = (shape: VenueShape): VenuePoint[] =>
  shape.type === "rect" ? rectToPoints(shape) : shape.points;

const averagePoint = (points: VenuePoint[]): VenuePoint => {
  if (points.length === 0) return [0, 0];
  const sum = points.reduce<VenuePoint>(
    (total, [x, y]) => [total[0] + x, total[1] + y],
    [0, 0],
  );
  return [sum[0] / points.length, sum[1] / points.length];
};

export const polygonCentroid = (points: VenuePoint[]): VenuePoint => {
  let doubleArea = 0;
  let x = 0;
  let y = 0;
  for (let index = 0; index < points.length; index += 1) {
    const [currentX, currentY] = points[index];
    const [nextX, nextY] = points[(index + 1) % points.length];
    const cross = currentX * nextY - nextX * currentY;
    doubleArea += cross;
    x += (currentX + nextX) * cross;
    y += (currentY + nextY) * cross;
  }
  if (doubleArea === 0) return averagePoint(points);
  return [x / (3 * doubleArea), y / (3 * doubleArea)];
};

export const shapeCentroid = (shape: VenueShape): VenuePoint =>
  shape.type === "rect"
    ? [shape.x + shape.w / 2, shape.y + shape.h / 2]
    : polygonCentroid(shape.points);

export const pointInPolygon = (
  [pointX, pointY]: VenuePoint,
  points: VenuePoint[],
): boolean => {
  let isInside = false;
  for (let index = 0; index < points.length; index += 1) {
    const [currentX, currentY] = points[index];
    const [previousX, previousY] =
      points[(index + points.length - 1) % points.length];
    const crossesRay = currentY > pointY !== previousY > pointY;
    if (!crossesRay) continue;
    const intersectionX =
      ((previousX - currentX) * (pointY - currentY)) / (previousY - currentY) +
      currentX;
    if (pointX < intersectionX) isInside = !isInside;
  }
  return isInside;
};

export const pointInShape = (point: VenuePoint, shape: VenueShape): boolean => {
  if (shape.type === "rect") {
    const [x, y] = point;
    return (
      x >= shape.x &&
      x <= shape.x + shape.w &&
      y >= shape.y &&
      y <= shape.y + shape.h
    );
  }
  return pointInPolygon(point, shape.points);
};

export const snapValue = (value: number, grid: number) =>
  grid > 0 ? Math.round(value / grid) * grid : value;

export const snapPoint = ([x, y]: VenuePoint, grid: number): VenuePoint => [
  snapValue(x, grid),
  snapValue(y, grid),
];

export const rectFromPoints = (
  [startX, startY]: VenuePoint,
  [endX, endY]: VenuePoint,
): VenueRectShape => ({
  type: "rect",
  x: Math.min(startX, endX),
  y: Math.min(startY, endY),
  w: Math.abs(endX - startX),
  h: Math.abs(endY - startY),
});

export const shapeBounds = (shape: VenueShape): VenueBounds => {
  const points = shapeToPoints(shape);
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
};

const translateShape = (
  shape: VenueShape,
  deltaX: number,
  deltaY: number,
): VenueShape =>
  shape.type === "rect"
    ? { ...shape, x: shape.x + deltaX, y: shape.y + deltaY }
    : {
        ...shape,
        points: shape.points.map(([x, y]): VenuePoint => [
          x + deltaX,
          y + deltaY,
        ]),
      };

export const translateShapeInsideBounds = (
  shape: VenueShape,
  deltaX: number,
  deltaY: number,
  width: number,
  height: number,
): VenueShape => {
  const bounds = shapeBounds(shape);
  const limitedX = clamp(deltaX, -bounds.minX, width - bounds.maxX);
  const limitedY = clamp(deltaY, -bounds.minY, height - bounds.maxY);
  return translateShape(shape, limitedX, limitedY);
};

export const clampPointToBounds = (
  [x, y]: VenuePoint,
  width: number,
  height: number,
): VenuePoint => [clamp(x, 0, width), clamp(y, 0, height)];

export const isShapeInsideBounds = (
  shape: VenueShape,
  width: number,
  height: number,
) => {
  const bounds = shapeBounds(shape);
  return (
    bounds.minX >= 0 &&
    bounds.minY >= 0 &&
    bounds.maxX <= width &&
    bounds.maxY <= height
  );
};
