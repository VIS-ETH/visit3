import { generateColors } from "@mantine/colors-generator";
import type { MantineThemeOverride } from "@mantine/core";

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
