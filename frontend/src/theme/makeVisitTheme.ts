import { generateColors } from "@mantine/colors-generator";
import type { MantineThemeOverride } from "@mantine/core";

export default function makeVisitTheme(
  primaryColor: string,
): MantineThemeOverride {
  return {
    primaryColor: "brand",
    colors: {
      brand: generateColors(primaryColor),
    },
    autoContrast: true,
  };
}
