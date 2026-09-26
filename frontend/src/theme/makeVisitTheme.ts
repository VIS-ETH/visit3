import { generateColors } from "@mantine/colors-generator";
import type { CSSVariablesResolver, MantineThemeOverride } from "@mantine/core";
import { readableGlow, readableInk } from "./contrast";

const panelStyles = {
  background: "var(--visit-panel-bg)",
  borderColor: "var(--visit-border)",
};

const controlStyles = {
  background: "var(--visit-control-bg)",
  borderColor: "var(--visit-border)",
};

const popoverStyles = {
  dropdown: panelStyles,
  arrow: {
    background: "var(--visit-panel-bg)",
    borderColor: "var(--visit-border)",
  },
};

const inputComponentNames = [
  "Input",
  "InputBase",
  "TextInput",
  "PasswordInput",
  "Textarea",
  "Select",
  "MultiSelect",
  "Autocomplete",
  "NumberInput",
  "FileInput",
  "ColorInput",
] as const;

export default function makeVisitTheme(
  primaryColor: string,
): MantineThemeOverride {
  const inputComponents = Object.fromEntries(
    inputComponentNames.map((name) => [
      name,
      {
        styles: {
          input: controlStyles,
        },
      },
    ]),
  );

  return {
    primaryColor: "brand",
    colors: {
      brand: generateColors(primaryColor),
    },
    autoContrast: true,
    components: {
      Paper: {
        styles: {
          root: panelStyles,
        },
      },
      Card: {
        styles: {
          root: panelStyles,
        },
      },
      Modal: {
        styles: {
          content: panelStyles,
          header: {
            background: "var(--visit-panel-bg)",
          },
          body: {
            background: "var(--visit-panel-bg)",
          },
        },
      },
      HoverCard: {
        styles: popoverStyles,
      },
      Popover: {
        styles: popoverStyles,
      },
      Menu: {
        styles: {
          dropdown: panelStyles,
        },
      },
      Combobox: {
        styles: {
          dropdown: panelStyles,
          search: controlStyles,
        },
      },
      Table: {
        defaultProps: {
          stripedColor: "transparent",
          highlightOnHoverColor: "var(--visit-table-row-hover-bg)",
        },
      },
      ...inputComponents,
    },
  };
}

const BODY_BACKGROUND = "#f7f8f9";
const DARK_BACKGROUNDS = ["#0f1318", "#171b20"];
const TEXT_CONTRAST = 4.6;
const TINTS_UNDER_TEXT = 3;
const TEXT_SHADE = 6;
const LIGHT_VARIANT_SHADE = 9;
const DIMMED_BACKGROUND_SHADES = 2;

export const visitCssVariablesResolver: CSSVariablesResolver = (theme) => {
  const lightBackgrounds = (shades: readonly string[]) => [
    "#ffffff",
    BODY_BACKGROUND,
    ...shades.slice(0, TINTS_UNDER_TEXT),
  ];
  const textColors = Object.entries(theme.colors).filter(
    ([name]) => name !== "dark",
  );
  const light: Record<string, string> = Object.fromEntries(
    textColors.flatMap(([name, shades]) => {
      const backgrounds = lightBackgrounds(shades);
      const ink = readableInk(shades[TEXT_SHADE], backgrounds, TEXT_CONTRAST);
      return [
        [`--mantine-color-${name}-text`, ink],
        [`--mantine-color-${name}-outline`, ink],
        [
          `--mantine-color-${name}-light-color`,
          readableInk(shades[LIGHT_VARIANT_SHADE], backgrounds, TEXT_CONTRAST),
        ],
      ];
    }),
  );
  return {
    variables: {},
    light: {
      ...light,
      "--mantine-color-anchor": light["--mantine-color-brand-text"],
      "--mantine-color-error": readableInk(
        theme.colors.red[TEXT_SHADE],
        ["#ffffff", BODY_BACKGROUND],
        TEXT_CONTRAST,
      ),
      "--mantine-color-dimmed": readableInk(
        theme.colors.gray[TEXT_SHADE],
        [
          "#ffffff",
          BODY_BACKGROUND,
          ...theme.colors.gray.slice(0, DIMMED_BACKGROUND_SHADES),
        ],
        TEXT_CONTRAST,
      ),
    },
    dark: {
      "--mantine-color-error": readableGlow(
        theme.colors.red[8],
        DARK_BACKGROUNDS,
        TEXT_CONTRAST,
      ),
    },
  };
};
