import { describe, expect, it } from "vitest";
import { DEFAULT_THEME, mergeMantineTheme } from "@mantine/core";
import { contrastRatio } from "../../theme/contrast";
import makeVisitTheme, {
  visitCssVariablesResolver,
} from "../../theme/makeVisitTheme";

const VIS_YELLOW = "#FFE210";
const BODY_BACKGROUND = "#f7f8f9";
const WCAG_AA_TEXT = 4.5;

const theme = mergeMantineTheme(DEFAULT_THEME, makeVisitTheme(VIS_YELLOW));
const { light, dark } = visitCssVariablesResolver(theme);
const lightToken = (token: string) => (light as Record<string, string>)[token];

const lowestContrast = (color: string, backgrounds: string[]) =>
  Math.min(
    ...backgrounds.map((background) => contrastRatio(color, background)),
  );

describe("the light theme text colours", () => {
  it.each([
    "--mantine-color-anchor",
    "--mantine-color-brand-text",
    "--mantine-color-brand-light-color",
    "--mantine-color-brand-outline",
  ])("keeps %s readable on white and brand tints", (token) => {
    const backgrounds = [
      "#ffffff",
      BODY_BACKGROUND,
      ...theme.colors.brand.slice(0, 3),
    ];

    expect(
      lowestContrast(lightToken(token), backgrounds),
    ).toBeGreaterThanOrEqual(WCAG_AA_TEXT);
  });

  it.each([
    "--mantine-color-yellow-text",
    "--mantine-color-yellow-light-color",
    "--mantine-color-yellow-outline",
  ])("keeps %s readable on white and yellow tints", (token) => {
    const backgrounds = [
      "#ffffff",
      BODY_BACKGROUND,
      ...theme.colors.yellow.slice(0, 3),
    ];

    expect(
      lowestContrast(lightToken(token), backgrounds),
    ).toBeGreaterThanOrEqual(WCAG_AA_TEXT);
  });

  it("keeps the yellow brand fill for buttons", () => {
    const shade =
      typeof theme.primaryShade === "number"
        ? theme.primaryShade
        : theme.primaryShade.light;

    expect(theme.colors.brand[shade].toLowerCase()).toBe(
      VIS_YELLOW.toLowerCase(),
    );
  });

  it("measures the WCAG ratio of plain colours", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 1);
    expect(contrastRatio("#ffe210", "#ffffff")).toBeLessThan(1.5);
  });

  it("leaves the dark theme untouched", () => {
    expect(dark).toEqual({});
  });
});
