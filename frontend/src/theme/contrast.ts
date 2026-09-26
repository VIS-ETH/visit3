import { darken, luminance } from "@mantine/core";

const DARKEN_STEP = 0.02;
const MAX_STEPS = 50;

export const contrastRatio = (foreground: string, background: string) => {
  const [lighter, darker] = [luminance(foreground), luminance(background)].sort(
    (a, b) => b - a,
  );
  return (lighter + 0.05) / (darker + 0.05);
};

export const readableInk = (
  color: string,
  backgrounds: string[],
  minimumRatio: number,
) => {
  const isReadable = (candidate: string) =>
    backgrounds.every(
      (background) => contrastRatio(candidate, background) >= minimumRatio,
    );
  for (let step = 0; step <= MAX_STEPS; step += 1) {
    const candidate = darken(color, step * DARKEN_STEP);
    if (isReadable(candidate)) return candidate;
  }
  return darken(color, 1);
};
