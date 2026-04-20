import { Button, type ButtonProps } from "@mantine/core";
import type { ElementType } from "react";

type AuthButtonProps = ButtonProps & {
  intent?: "primary" | "secondary";
  component?: ElementType;
  to?: string;
  href?: string;
  [key: string]: unknown;
};

export default function AuthButton({
  intent = "primary",
  size,
  fullWidth,
  color,
  variant,
  styles,
  ...props
}: AuthButtonProps) {
  const baseRootStyles = {
    minHeight: 46,
    borderRadius: 10,
    fontWeight: 600,
  };

  const secondaryStyles = {
    root: {
      ...baseRootStyles,
      background: "var(--visit-auth-btn-secondary-bg)",
      border: "1px solid var(--visit-auth-btn-secondary-border)",
      color: "var(--visit-auth-btn-secondary-text)",
      "&:hover": {
        background: "var(--visit-auth-btn-secondary-hover)",
      },
    },
    label: {
      whiteSpace: "normal",
      lineHeight: 1.25,
    },
  };

  const primaryStyles = {
    root: {
      ...baseRootStyles,
      color: "var(--visit-auth-btn-primary-text)",
    },
  };

  return (
    <Button
      size={size ?? "md"}
      fullWidth={fullWidth ?? true}
      color={color ?? "brand"}
      variant={variant ?? (intent === "secondary" ? "light" : "filled")}
      styles={
        styles ?? (intent === "secondary" ? secondaryStyles : primaryStyles)
      }
      {...(props as Record<string, unknown>)}
    />
  );
}
