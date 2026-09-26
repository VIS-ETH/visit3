import { describe, expect, it } from "vitest";
import { DEFAULT_THEME, mergeMantineTheme } from "@mantine/core";
import { contrastRatio } from "../../theme/contrast";
import makeVisitTheme, {
  visitCssVariablesResolver,
} from "../../theme/makeVisitTheme";

const VIS_YELLOW = "#FFE210";
const BODY_BACKGROUND = "#f7f8f9";
const DARK_BACKGROUNDS = ["#0f1318", "#171b20"];
const WCAG_AA_TEXT = 4.5;
const PRIMARY_TEXT_CONTRAST = 7;

const theme = mergeMantineTheme(DEFAULT_THEME, makeVisitTheme(VIS_YELLOW));
const { light, dark } = visitCssVariablesResolver(theme);
const lightToken = (token: string) => (light as Record<string, string>)[token];
const darkToken = (token: string) => (dark as Record<string, string>)[token];
const TEXT_COLORS = Object.keys(theme.colors).filter((name) => name !== "dark");

const lowestContrast = (color: string, backgrounds: string[]) =>
  Math.min(
    ...backgrounds.map((background) => contrastRatio(color, background)),
  );

describe("the light theme text colours", () => {
  it.each(
    TEXT_COLORS.flatMap((name) => [
      [name, `--mantine-color-${name}-text`],
      [name, `--mantine-color-${name}-light-color`],
      [name, `--mantine-color-${name}-outline`],
    ]),
  )("keeps the %s token %s readable on white and its tints", (name, token) => {
    const backgrounds = [
      "#ffffff",
      BODY_BACKGROUND,
      ...theme.colors[name].slice(0, 3),
    ];

    expect(
      lowestContrast(lightToken(token), backgrounds),
    ).toBeGreaterThanOrEqual(WCAG_AA_TEXT);
  });

  it("keeps links readable on white and brand tints", () => {
    const backgrounds = [
      "#ffffff",
      BODY_BACKGROUND,
      ...theme.colors.brand.slice(0, 3),
    ];

    expect(
      lowestContrast(lightToken("--mantine-color-anchor"), backgrounds),
    ).toBeGreaterThanOrEqual(WCAG_AA_TEXT);
  });

  it("keeps error text readable", () => {
    expect(
      lowestContrast(lightToken("--mantine-color-error"), [
        "#ffffff",
        BODY_BACKGROUND,
      ]),
    ).toBeGreaterThanOrEqual(WCAG_AA_TEXT);
  });

  it("keeps dimmed text readable but still secondary", () => {
    const dimmed = lightToken("--mantine-color-dimmed");
    const backgrounds = [
      "#ffffff",
      BODY_BACKGROUND,
      ...theme.colors.gray.slice(0, 2),
    ];

    expect(lowestContrast(dimmed, backgrounds)).toBeGreaterThanOrEqual(
      WCAG_AA_TEXT,
    );
    expect(contrastRatio(dimmed, "#ffffff")).toBeLessThan(
      PRIMARY_TEXT_CONTRAST,
    );
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
});

describe("the dark theme text colours", () => {
  it("keeps error text readable on the dark panels", () => {
    expect(
      lowestContrast(darkToken("--mantine-color-error"), DARK_BACKGROUNDS),
    ).toBeGreaterThanOrEqual(WCAG_AA_TEXT);
  });

  it("changes nothing but the error colour", () => {
    expect(Object.keys(dark)).toEqual(["--mantine-color-error"]);
  });
});
