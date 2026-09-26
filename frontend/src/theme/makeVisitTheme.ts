import { generateColors } from "@mantine/colors-generator";
import type { CSSVariablesResolver, MantineThemeOverride } from "@mantine/core";
import { readableInk } from "./contrast";

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
const TEXT_CONTRAST = 4.6;
const INKED_COLORS = ["brand", "yellow"] as const;

export const visitCssVariablesResolver: CSSVariablesResolver = (theme) => {
  const inkFor = (name: (typeof INKED_COLORS)[number]) => {
    const shades = theme.colors[name];
    return readableInk(
      shades[9],
      ["#ffffff", BODY_BACKGROUND, ...shades.slice(0, 3)],
      TEXT_CONTRAST,
    );
  };
  const brandInk = inkFor("brand");
  const light = Object.fromEntries(
    INKED_COLORS.flatMap((name) => {
      const ink = inkFor(name);
      return [
        [`--mantine-color-${name}-text`, ink],
        [`--mantine-color-${name}-light-color`, ink],
        [`--mantine-color-${name}-outline`, ink],
      ];
    }),
  );
  return {
    variables: {},
    light: { ...light, "--mantine-color-anchor": brandInk },
    dark: {},
  };
};
